from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parent
APP_NAME = "dignity_machine_web"
USER_ID = "local_tester"

DEFAULT_QUERY = (
    "Analyze the selected disability denial case and prepare the advocate review summary. "
    "Use scoped case tools for case documents and Elastic tools for SSA policy, forms, and advocate contact."
)
MISSION_QUERIES = {
    "analyze_denial": (
        "Explain what the selected denial says. Focus only on the denial reason, "
        "evidence the notice mentions, plain-language SSA explanation, and directly relevant policy."
    ),
    "find_missing_evidence": (
        "Identify possible missing proof for the selected case. Keep denial context to one short line. "
        "Convert each possible proof gap into a task."
    ),
    "draft_records_request": (
        "Draft a concise doctor or clinic records request. Identify records needed and placeholder "
        "fields that were not present in the uploaded denial."
    ),
    "prepare_review_summary": DEFAULT_QUERY,
}
MISSION_ALIASES = {"prepare_packet": "prepare_review_summary"}
QUICK_RESPONSE = (
    "Hi. This UI is wired for selected-case denial analysis. "
    "Use a mission button to run Gemini with Elastic-backed tools. Short greetings "
    "are answered locally and do not call the agent."
)
DENIAL_TOOL_NAMES = """
Available tools for this mission. Use these exact names only:
- list_case_documents
- search_case_documents
- list_case_facts
- dignity_search_ssa_policy

Never abbreviate, pluralize, rename, or partially type a tool name. The SSA policy
search tool is exactly dignity_search_ssa_policy.
"""
ORCHESTRATOR_TOOL_NAMES = """
Available tools for this mission. Use these exact names only:
- list_case_documents
- search_case_documents
- list_case_facts
- dignity_search_ssa_policy
- dignity_search_ssa_forms
- dignity_get_advocate_contact
- dignity_search_case_memory

Never abbreviate, pluralize, rename, or partially type a tool name. The SSA policy
search tool is exactly dignity_search_ssa_policy.
"""


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, value = line.split("=", 1)
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key.strip()] = value
    return values


for key, value in load_dotenv(ROOT / ".env").items():
    os.environ.setdefault(key, value)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "integral-tensor-497618-a8")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

from case_services import (  # noqa: E402
    CaseError,
    CaseService,
    ElasticCaseStore,
    PdfTextExtractionError,
    PdfTextExtractor,
    PdfRelevanceError,
    PdfValidationError,
)
from dignity_agent.agent import build_agents  # noqa: E402


class AnalyzeRequest(BaseModel):
    case_id: str
    mission: str = "prepare_review_summary"
    query: str | None = None
    writeback: bool = False


class CaseFactInput(BaseModel):
    field: str
    label: str | None = None
    value: str
    source: str = "user_answer"


class CaseFactsRequest(BaseModel):
    facts: list[CaseFactInput]


class TaskStatusRequest(BaseModel):
    task_type: str
    to_status: str
    note: str | None = None


class CaseActionRequest(BaseModel):
    action_type: str
    payload: dict[str, Any] = {}


app = FastAPI(title="Dignity Machine")
app.mount("/assets", StaticFiles(directory=ROOT / "static" / "assets"), name="assets")
app.mount("/documents", StaticFiles(directory=ROOT / "static" / "documents"), name="documents")
session_service = InMemorySessionService()
runner_lock = asyncio.Lock()
case_store = ElasticCaseStore()
case_service = CaseService(case_store, PdfTextExtractor())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def stable_task_id(title: str, reason: str = "") -> str:
    seed = re.sub(r"[^a-z0-9]+", "_", f"{title} {reason}".lower()).strip("_")
    return f"task_{seed[:48] or uuid.uuid4().hex[:12]}"


def stable_fact_id(case_id: str, field: str) -> str:
    seed = re.sub(r"[^a-z0-9]+", "_", f"{case_id}_{field}".lower()).strip("_")
    return f"fact_{seed[:72] or uuid.uuid4().hex[:12]}"


TASK_TYPES = {
    "missing_proof",
    "missing_notice_date",
    "missing_denial_reason",
    "missing_condition",
    "missing_appeal_stage",
    "missing_provider",
    "records_request_review",
    "review_summary_review",
}
TASK_STATUSES = {"suggested", "needs_info", "draft_created", "ready_for_review"}
TASK_SOURCES = {"denial_letter", "ssa_policy", "agent_inference"}
FACT_SOURCES = {"user_answer", "agent_extraction", "denial_letter"}
CASE_ACTION_TYPES = {"google_calendar_opened", "mailto_opened", "fact_saved", "task_status_updated"}
TASK_UPDATE_STATUSES = {"done", "not_relevant", "needs_info", "suggested", "draft_created", "ready_for_review"}


def canonical_mission(mission: str) -> str:
    return MISSION_ALIASES.get(mission, mission)


def as_plain_text(event: Any) -> str:
    if not getattr(event, "content", None) or not event.content.parts:
        return ""
    return "".join(part.text or "" for part in event.content.parts).strip()


def clean_json_text(value: str) -> str:
    value = value.strip()
    code_match = re.search(r"```(?:json)?\s*(.*?)```", value, flags=re.DOTALL | re.IGNORECASE)
    if code_match:
        value = code_match.group(1).strip()
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        value = value[start : end + 1]
    return value


def escape_json_control_chars(value: str) -> str:
    result: list[str] = []
    in_string = False
    escaped = False
    for char in value:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            continue
        if char == '"':
            result.append(char)
            in_string = not in_string
            continue
        if in_string:
            if char == "\n":
                result.append("\\n")
                continue
            if char == "\r":
                result.append("\\r")
                continue
            if char == "\t":
                result.append("\\t")
                continue
            if ord(char) < 32:
                result.append(f"\\u{ord(char):04x}")
                continue
        result.append(char)
    return "".join(result)


def parse_agent_json(value: str) -> dict[str, Any]:
    cleaned = clean_json_text(value)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = escape_json_control_chars(cleaned)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail=f"Agent did not return valid JSON: {exc}\n\n{value[:1200]}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="Agent JSON response was not an object.")
    return parsed


def try_parse_agent_json(value: str) -> dict[str, Any] | None:
    try:
        return parse_agent_json(value)
    except HTTPException:
        return None


def normalize_ssa_url(url: Any) -> Any:
    if not isinstance(url, str):
        return url
    url = re.sub(
        r"http://policy\.ssa\.gov/poms\.nsf/lnx/([0-9A-Za-z]+)",
        r"https://secure.ssa.gov/apps10/poms.nsf/lnx/\1",
        url,
        flags=re.IGNORECASE,
    )
    url = re.sub(
        r"https://policy\.ssa\.gov/poms\.nsf/lnx/([0-9A-Za-z]+)",
        r"https://secure.ssa.gov/apps10/poms.nsf/lnx/\1",
        url,
        flags=re.IGNORECASE,
    )
    url = url.replace("http://secure.ssa.gov/", "https://secure.ssa.gov/")
    url = url.replace("https://secure.ssa.gov/poms.NSF/", "https://secure.ssa.gov/apps10/poms.nsf/")
    url = url.replace("https://secure.ssa.gov/poms.nsf/", "https://secure.ssa.gov/apps10/poms.nsf/")
    return url


def normalize_urls_deep(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_ssa_url(value)
    if isinstance(value, list):
        return [normalize_urls_deep(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_urls_deep(item) for key, item in value.items()}
    return value


def normalize_structured_urls(structured: dict[str, Any]) -> dict[str, Any]:
    return normalize_urls_deep(structured)


def remove_unsupported_medical_evidence(structured: dict[str, Any], case_id: str) -> dict[str, Any]:
    """Keep medical_evidence limited to actual medical case documents.

    The agent can summarize denial letters, but denial letters are not doctor
    records. This prevents denial-only PDFs from being displayed as medical
    findings in the UI.
    """
    try:
        inventory = case_store.list_documents(case_id, limit=50)
    except Exception as exc:
        print(f"[WARN] Could not validate medical_evidence for {case_id}: {exc}")
        return structured

    allowed_types = {"medical_record", "medication_list"}
    docs_by_id = {
        str(doc.get("doc_id")): doc
        for doc in inventory.get("documents", [])
        if doc.get("doc_id")
    }
    allowed_doc_ids = {
        doc_id
        for doc_id, doc in docs_by_id.items()
        if str(doc.get("document_type") or "") in allowed_types
    }

    filtered: list[dict[str, Any]] = []
    removed: list[str] = []
    for item in structured.get("medical_evidence", []) or []:
        if not isinstance(item, dict):
            continue
        doc_id = str(item.get("doc_id") or "")
        if doc_id in allowed_doc_ids:
            filtered.append(item)
        elif doc_id:
            removed.append(doc_id)

    if removed:
        structured.setdefault("case_document_warnings", []).append(
            {
                "type": "unsupported_medical_evidence_removed",
                "doc_ids": sorted(set(removed)),
                "message": "Removed medical_evidence entries that pointed to non-medical case documents.",
            }
        )
    structured["medical_evidence"] = filtered
    return structured


def remove_unavailable_advocate_alert(structured: dict[str, Any], case_id: str) -> dict[str, Any]:
    alert = str(structured.get("advocate_alert_draft") or "").strip()
    if not alert:
        return structured
    try:
        result = elastic_request_json(
            "POST",
            "/advocate_contacts/_count",
            {"query": {"term": {"case_id": case_id}}},
        )
    except Exception as exc:
        print(f"[WARN] Could not validate advocate contact for {case_id}: {exc}")
        return structured

    if int(result.get("count", 0)) > 0:
        return structured

    structured["advocate_alert_draft"] = ""
    structured.setdefault("case_document_warnings", []).append(
        {
            "type": "advocate_alert_removed",
            "message": "Removed advocate alert draft because no advocate contact exists for the selected case.",
        }
    )
    next_actions = structured.get("next_actions")
    if isinstance(next_actions, list):
        reminder = "Add a trusted advocate contact before drafting or sending an advocate alert."
        if reminder not in next_actions:
            next_actions.append(reminder)
    return structured


def unsupported_terms(generated_text: str, case_text: str) -> list[str]:
    case_lower = case_text.lower()
    generated_lower = generated_text.lower()
    terms: set[str] = set()
    invalid_provider_name_parts = {
        "a",
        "an",
        "and",
        "claimant",
        "evidence",
        "he",
        "medical",
        "she",
        "the",
        "they",
        "this",
    }
    for match in re.finditer(r"\bDr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", generated_text):
        name = match.group(0)
        last = name.split()[-1]
        if last.lower() in invalid_provider_name_parts:
            continue
        if name.lower() not in case_lower:
            terms.add(name)
            if len(last) > 2:
                terms.add(last)
    if re.search(r"\bDr\.(?:\s|\"|,|\.|$)", generated_text) and "dr." not in case_lower:
        terms.add("Dr.")
    for phrase in (
        "findings from treating physician",
        "normal physical examination",
        "normal physical examination results",
        "normal muscle strength",
        "full range of motion",
        "joint swelling",
        "reported daily activities",
        "primary care physician",
        "treating physician",
        "treating source",
    ):
        if phrase in generated_lower and phrase not in case_lower:
            terms.add(phrase)
    return sorted(terms, key=len, reverse=True)


def strip_sentences_with_terms(value: str, terms: list[str]) -> str:
    if not value or not terms:
        return value
    pieces = re.split(r"(?<=[.!?])\s+", value)
    kept = [
        piece
        for piece in pieces
        if piece and not any(term.lower() in piece.lower() for term in terms)
    ]
    return " ".join(kept).strip()


def remove_unsupported_generated_case_claims(structured: dict[str, Any], case_id: str) -> dict[str, Any]:
    generated_text = json.dumps(structured, ensure_ascii=False)
    try:
        case_text = case_store.case_text(case_id)
    except Exception as exc:
        print(f"[WARN] Could not validate generated case claims for {case_id}: {exc}")
        return structured

    terms = unsupported_terms(generated_text, case_text)
    if not terms:
        return structured

    for key in ("denial_summary", "records_request_draft", "packet_summary", "review_summary"):
        if isinstance(structured.get(key), str):
            structured[key] = strip_sentences_with_terms(structured[key], terms)

    filtered_policies = []
    for citation in structured.get("policy_citations", []) or []:
        if not isinstance(citation, dict):
            continue
        why = str(citation.get("why_it_matters", "") or "")
        if any(term.lower() in why.lower() for term in terms):
            continue
        filtered_policies.append(citation)
    structured["policy_citations"] = filtered_policies

    filtered_gaps = []
    for gap in structured.get("missing_evidence", []) or []:
        if not isinstance(gap, dict):
            continue
        gap_text = json.dumps(gap, ensure_ascii=False)
        if any(term.lower() in gap_text.lower() for term in terms):
            continue
        filtered_gaps.append(gap)
    structured["missing_evidence"] = filtered_gaps

    next_actions = structured.get("next_actions")
    if isinstance(next_actions, list):
        structured["next_actions"] = [
            item
            for item in next_actions
            if not any(term.lower() in str(item).lower() for term in terms)
        ]

    structured.setdefault("case_document_warnings", []).append(
        {
            "type": "unsupported_generated_claims_removed",
            "terms": terms,
            "message": "Removed generated claims that used names or examination details not present in selected case documents.",
        }
    )
    return structured


def parse_loose_date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    match = re.search(r"\b([A-Z][a-z]+ \d{1,2}, \d{4})\b", text)
    if match:
        try:
            return datetime.strptime(match.group(1), "%B %d, %Y")
        except ValueError:
            return None
    return None


def list_case_facts(case_id: str) -> list[dict[str, Any]]:
    try:
        result = elastic_request_json(
            "POST",
            "/case_facts/_search",
            {
                "query": {"term": {"case_id": case_id}},
                "sort": [{"updated_at": {"order": "desc"}}, {"created_at": {"order": "desc"}}],
                "size": 100,
            },
        )
    except RuntimeError as exc:
        if "index_not_found_exception" not in str(exc) and "HTTP 404" not in str(exc):
            raise
        return []
    return [hit.get("_source", {}) for hit in result.get("hits", {}).get("hits", [])]


def case_fact_map(case_id: str) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    for fact in list_case_facts(case_id):
        field = str(fact.get("field", ""))
        if field and field not in facts:
            facts[field] = fact
    return facts


def fact_value(facts: dict[str, dict[str, Any]], field: str) -> str:
    value = facts.get(field, {}).get("value", "")
    return str(value or "").strip()


def find_notice_date(case_text: str) -> datetime | None:
    for pattern in (
        r"\bDate:\s*([A-Z][a-z]+ \d{1,2}, \d{4})",
        r"\bNotice Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})",
        r"\bdated\s+([A-Z][a-z]+ \d{1,2}, \d{4})",
    ):
        match = re.search(pattern, case_text)
        if match:
            parsed = parse_loose_date(match.group(1))
            if parsed:
                return parsed
    return None


def iso_date(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d") if value else None


def normalize_deadline(structured: dict[str, Any], case_id: str, facts: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        case_text = case_store.case_text(case_id)
    except Exception as exc:
        print(f"[WARN] Could not inspect case text for deadline {case_id}: {exc}")
        case_text = ""
    if facts is None:
        facts = case_fact_map(case_id)

    raw_deadline = structured.get("deadline")
    if not isinstance(raw_deadline, dict):
        raw_deadline = {}

    fact_notice_date = parse_loose_date(fact_value(facts, "notice_date"))
    notice_date = fact_notice_date or parse_loose_date(raw_deadline.get("notice_date")) or find_notice_date(case_text)
    assumed_receipt_date = parse_loose_date(raw_deadline.get("assumed_receipt_date"))
    appeal_deadline = parse_loose_date(raw_deadline.get("appeal_deadline"))
    source = str(raw_deadline.get("source") or "").strip()

    if notice_date and not assumed_receipt_date:
        assumed_receipt_date = notice_date + timedelta(days=5)
    if assumed_receipt_date and not appeal_deadline:
        appeal_deadline = assumed_receipt_date + timedelta(days=60)
    if fact_notice_date:
        source = "user_answer"
    elif notice_date and not source:
        source = "denial_letter"

    structured["deadline"] = {
        "notice_date": iso_date(notice_date),
        "assumed_receipt_date": iso_date(assumed_receipt_date),
        "appeal_deadline": iso_date(appeal_deadline),
        "confidence": float(raw_deadline.get("confidence", 0.75 if notice_date else 0.2) or 0.2),
        "source": source or "agent_inference",
        "human_review_required": True,
    }
    return structured


def normalize_case_tasks(structured: dict[str, Any], case_text: str = "", facts: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    facts = facts or {}

    def add_task(
        task_type: str,
        title: str,
        description: str,
        reason: str,
        source: str,
        status: str,
        derived_from_gap: bool = False,
    ) -> None:
        title = re.sub(r"\s+", " ", str(title or "")).strip()
        description = re.sub(r"\s+", " ", str(description or "")).strip()
        reason = re.sub(r"\s+", " ", str(reason or "")).strip()
        if not title:
            return
        if task_type not in TASK_TYPES:
            task_type = "missing_proof" if derived_from_gap else "missing_provider"
        if status not in TASK_STATUSES:
            status = "suggested" if task_type == "missing_proof" else "needs_info"
        source = source if source in TASK_SOURCES else "agent_inference"
        key = f"{task_type}:{title.lower()}"
        if key in seen:
            return
        seen.add(key)
        tasks.append(
            {
                "task_id": stable_task_id(title, reason),
                "task_type": task_type,
                "title": title,
                "description": description or title,
                "reason": reason or "Generated from selected case analysis.",
                "status": status,
                "source": source,
            }
        )

    for raw in structured.get("case_tasks", []) or []:
        if not isinstance(raw, dict):
            continue
        add_task(
            "missing_proof",
            raw.get("title", ""),
            raw.get("description", ""),
            raw.get("reason", ""),
            raw.get("source", "agent_inference"),
            "suggested",
            derived_from_gap=True,
        )

    deadline = structured.get("deadline") if isinstance(structured.get("deadline"), dict) else {}
    if not deadline.get("notice_date"):
        add_task(
            "missing_notice_date",
            "Find notice date",
            "Locate the notice date on the denial letter before relying on any appeal deadline.",
            "The agent could not confirm a notice date from the selected PDF.",
            "denial_letter",
            "needs_info",
        )

    denial_summary = str(structured.get("denial_summary") or "").strip()
    saved_denial_reason = fact_value(facts, "denial_reason")
    reason_text = f"{denial_summary}\n{case_text}\n{saved_denial_reason}".lower()
    if not any(term in reason_text for term in ("denied", "not disabled", "insufficient", "does not show", "does not demonstrate", "work")):
        add_task(
            "missing_denial_reason",
            "Confirm denial reason",
            "Identify the exact reason the notice gives for denying benefits.",
            "The denial reason was not clear enough in the generated summary.",
            "denial_letter",
            "needs_info",
        )

    combined_text = " ".join(
        str(value or "")
        for value in (
            case_text,
            structured.get("denial_summary"),
            structured.get("packet_summary"),
            " ".join(str(fact.get("value", "")) for fact in facts.values()),
            json.dumps(structured.get("missing_evidence", []), ensure_ascii=False),
        )
    ).lower()
    condition_terms = (
        "fibromyalgia",
        "migraine",
        "depression",
        "anxiety",
        "ptsd",
        "back pain",
        "arthritis",
        "diabetes",
        "heart",
        "cancer",
        "bipolar",
        "schizophrenia",
        "asthma",
        "copd",
        "stroke",
        "seizure",
    )
    if not any(term in combined_text for term in condition_terms):
        add_task(
            "missing_condition",
            "Confirm main condition",
            "Identify the medical condition or impairment the denial is based on.",
            "The selected PDF or generated summary did not clearly name the main condition.",
            "denial_letter",
            "needs_info",
        )

    if not any(term in combined_text for term in ("reconsideration", "hearing", "appeal", "initial claim", "initial denial", "initial-level", "appeals council", "review your claim again")):
        add_task(
            "missing_appeal_stage",
            "Confirm appeal stage",
            "Identify whether this case is at initial denial, reconsideration, hearing, or another appeal stage.",
            "The selected PDF did not clearly identify the appeal stage.",
            "denial_letter",
            "needs_info",
        )

    provider_pattern = re.compile(r"\b(Dr\.|doctor|clinic|hospital|medical center|health center|physician|rheumatology|neurology|primary care)\b", re.IGNORECASE)
    provider_name = fact_value(facts, "provider_name")
    if not provider_name and not provider_pattern.search(combined_text):
        add_task(
            "missing_provider",
            "Confirm doctor or clinic names",
            "Find the provider, clinic, or office names needed for records requests.",
            "The selected PDF did not clearly identify doctor or clinic names.",
            "denial_letter",
            "needs_info",
        )

    for gap in structured.get("missing_evidence", []) or []:
        if not isinstance(gap, dict):
            continue
        gap_type = str(gap.get("gap_type") or gap.get("item") or "Missing proof").strip()
        description = str(gap.get("description") or gap.get("reason") or "").strip()
        why = str(gap.get("why_it_matters") or "This gap may affect whether the denial can be challenged.").strip()
        add_task(
            "missing_proof",
            f"Gather {gap_type}",
            description or f"Gather evidence for: {gap_type}.",
            why,
            "agent_inference",
            "suggested",
            derived_from_gap=True,
        )

    if structured.get("records_request_draft"):
        add_task(
            "records_request_review",
            "Review doctor records request",
            "Check the generated records request before sending it to any provider.",
            "The request is a draft and needs human review.",
            "agent_inference",
            "draft_created",
        )

    if structured.get("packet_summary") or structured.get("review_summary"):
        add_task(
            "review_summary_review",
            "Review generated summary",
            "Review the generated case summary before using it in an appeal workflow.",
            "Agent output is not legal advice and needs human review.",
            "agent_inference",
            "ready_for_review",
        )

    structured["case_tasks"] = tasks
    return structured


def normalize_action_plan(structured: dict[str, Any], case_id: str) -> dict[str, Any]:
    facts = case_fact_map(case_id)
    structured = normalize_deadline(structured, case_id, facts)
    try:
        case_text = case_store.case_text(case_id)
    except Exception as exc:
        print(f"[WARN] Could not inspect case text for action tasks {case_id}: {exc}")
        case_text = ""
    structured = normalize_case_tasks(structured, case_text, facts)
    return structured


def mission_scoped_structured(structured: dict[str, Any], mission: str, case_id: str) -> dict[str, Any]:
    mission = canonical_mission(mission)
    structured["mission"] = mission
    if "packet_summary" in structured and "review_summary" not in structured:
        structured["review_summary"] = structured.get("packet_summary")
    facts = case_fact_map(case_id)

    def string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    if mission == "analyze_denial":
        return {
            "mission": mission,
            "denial_summary": str(structured.get("denial_summary", "")),
            "denial_reason": str(structured.get("denial_reason", "")),
            "ssa_explanation": str(structured.get("ssa_explanation", "")),
            "evidence_mentioned": string_list(structured.get("evidence_mentioned")),
            "policy_citations": structured.get("policy_citations", []) or [],
            "human_review_note": str(structured.get("human_review_note", "Generated explanation requires human review.")),
        }

    if mission == "find_missing_evidence":
        scoped = {
            "mission": mission,
            "case_context": str(structured.get("case_context") or structured.get("denial_summary") or ""),
            "missing_evidence": structured.get("missing_evidence", []) or [],
            "case_tasks": structured.get("case_tasks", []) or [],
            "human_review_note": str(structured.get("human_review_note", "Possible gaps require human review.")),
        }
        try:
            case_text = case_store.case_text(case_id)
        except Exception as exc:
            print(f"[WARN] Could not inspect case text for missing-evidence tasks {case_id}: {exc}")
            case_text = ""
        return normalize_case_tasks(scoped, case_text, facts)

    if mission == "draft_records_request":
        try:
            case_text = case_store.case_text(case_id)
        except Exception as exc:
            print(f"[WARN] Could not inspect case text for records request {case_id}: {exc}")
            case_text = ""
        records_needed = string_list(structured.get("records_needed"))
        if not records_needed:
            records_needed = ["Medical records referenced by the denial letter"]
        placeholder_fields = string_list(structured.get("placeholder_fields"))
        provider_name = fact_value(facts, "provider_name")
        provider_pattern = re.compile(r"\b(Dr\.|doctor|clinic|hospital|medical center|health center|physician|rheumatology|neurology|primary care)\b", re.IGNORECASE)
        if provider_name:
            placeholder_fields = [field for field in placeholder_fields if field.lower() not in {"doctor or clinic name", "provider name", "provider/clinic"}]
        elif not provider_pattern.search(case_text) and "Doctor or clinic name" not in placeholder_fields:
            placeholder_fields.append("Doctor or clinic name")
        if "Patient date of birth" not in placeholder_fields:
            placeholder_fields.append("Patient date of birth")
        request_context = str(structured.get("request_context") or structured.get("case_context") or "")
        draft = str(structured.get("records_request_draft", ""))
        if provider_name and provider_name.lower() not in draft.lower():
            draft = f"Provider/clinic: {provider_name}\n\n{draft}".strip()
        if provider_name and provider_name.lower() not in request_context.lower():
            request_context = f"{request_context} Provider/clinic saved by user: {provider_name}.".strip()
        return {
            "mission": mission,
            "request_context": request_context,
            "records_needed": records_needed,
            "placeholder_fields": placeholder_fields,
            "records_request_draft": draft,
            "human_review_note": str(structured.get("human_review_note", "This request is a draft for human review.")),
        }

    scoped = {
        "mission": mission,
        "denial_summary": str(structured.get("denial_summary", "")),
        "policy_citations": structured.get("policy_citations", []) or [],
        "missing_evidence": structured.get("missing_evidence", []) or [],
        "deadline": structured.get("deadline") or {},
        "case_tasks": structured.get("case_tasks", []) or [],
        "records_request_draft": str(structured.get("records_request_draft", "")),
        "review_summary": str(structured.get("review_summary") or ""),
        "next_actions": string_list(structured.get("next_actions")),
        "human_review_note": str(structured.get("human_review_note", "Generated review summary requires human review.")),
    }
    provider_name = fact_value(facts, "provider_name")
    if provider_name and provider_name.lower() not in scoped["records_request_draft"].lower():
        scoped["records_request_draft"] = f"Provider/clinic: {provider_name}\n\n{scoped['records_request_draft']}".strip()
    scoped["case_facts"] = list(facts.values())
    return normalize_action_plan(scoped, case_id)


def build_action_events(structured: dict[str, Any], mission_id: str, case_id: str, writeback_enabled: bool, mission: str) -> list[dict[str, Any]]:
    created_at = now_iso()
    events: list[dict[str, Any]] = []

    def add(event_type: str, result: str, output: dict[str, Any] | None = None) -> None:
        events.append(
            {
                "event_id": stable_id("event"),
                "case_id": case_id,
                "mission_id": mission_id,
                "event_type": event_type,
                "tool_name": "action_plan",
                "index_name": "case_workspace",
                "input": {},
                "output": {"result": result, **(output or {})},
                "created_at": created_at,
            }
        )

    mission = canonical_mission(mission)
    add("case_text_indexed", "Saved extracted text to Elastic")
    add("case_text_searched", "Searched selected case text")
    saved_facts = structured.get("case_facts", []) or []
    if saved_facts:
        add("case_facts_loaded", "Loaded saved case facts", {"count": len(saved_facts)})
    if mission == "analyze_denial":
        add("denial_analyzed", "Explained denial")
    if mission in {"analyze_denial", "prepare_review_summary"} and structured.get("policy_citations"):
        add("policy_searched", "Searched SSA policy", {"count": len(structured.get("policy_citations", []) or [])})
    if mission in {"find_missing_evidence", "prepare_review_summary"} and structured.get("missing_evidence"):
        add("evidence_gap_created", "Found possible missing proof", {"count": len(structured.get("missing_evidence", []) or [])})
    deadline = structured.get("deadline") if isinstance(structured.get("deadline"), dict) else {}
    if mission == "prepare_review_summary" and deadline.get("appeal_deadline"):
        add("deadline_created", "Created possible appeal deadline", {"appeal_deadline": deadline.get("appeal_deadline")})
    elif mission == "prepare_review_summary":
        add("deadline_needed", "Created task to find notice date")
    if mission in {"find_missing_evidence", "prepare_review_summary"} and structured.get("case_tasks"):
        add("case_tasks_created", "Created action tasks", {"count": len(structured.get("case_tasks", []) or [])})
    if mission in {"draft_records_request", "prepare_review_summary"} and structured.get("records_request_draft"):
        add("records_request_drafted", "Drafted records request")
    if mission == "prepare_review_summary" and (structured.get("review_summary") or structured.get("denial_summary")):
        add("review_summary_created", "Created review summary")
    if writeback_enabled:
        add("action_plan_saved", "Saved mission output to Elastic")
    return events


def quick_local_response(query: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9 ]+", "", query.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    quick_inputs = {
        "",
        "hi",
        "hello",
        "hey",
        "yo",
        "test",
        "ping",
        "hi there",
        "hello there",
    }
    if normalized in quick_inputs:
        return QUICK_RESPONSE
    if len(normalized.split()) <= 3 and normalized.startswith(("hi ", "hello ", "hey ")):
        return QUICK_RESPONSE
    return None


def mission_instructions(mission: str) -> str:
    if mission == "analyze_denial":
        return (
            "This mission is ONLY denial explanation. Explain what the denial says. "
            "Do not identify missing proof tasks, calculate deadlines, draft records requests, "
            "or create a review summary."
        )
    if mission == "find_missing_evidence":
        return (
            "This mission is ONLY missing-proof analysis. Keep case_context to one short line. "
            "Return possible missing evidence and matching case tasks. Do not draft a records "
            "request or create a review summary."
        )
    if mission == "draft_records_request":
        return (
            "This mission is ONLY records-request drafting. Identify records needed, placeholder "
            "fields, and a concise records_request_draft. Do not provide full missing-proof "
            "analysis, deadline analysis, or a review summary."
        )
    return (
        "This mission is full combined review-summary preparation. Include denial summary, policy, "
        "missing evidence, deadline, case tasks, records request draft, review summary, and next actions."
    )


def policy_citation_schema() -> str:
    return """[
    {
      "doc_id": "string",
      "chunk_id": "string or null",
      "title": "string",
      "url": "string or null",
      "why_it_matters": "string"
    }
  ]"""


def missing_evidence_schema() -> str:
    return """[
    {
      "gap_type": "string",
      "description": "string",
      "why_it_matters": "string",
      "supporting_policy_ids": ["string"],
      "supporting_case_doc_ids": ["string"],
      "confidence": 0.0
    }
  ]"""


def case_tasks_schema() -> str:
    return """[
    {
      "task_id": "string",
      "task_type": "missing_proof",
      "title": "string",
      "description": "string",
      "reason": "string",
      "status": "suggested",
      "source": "denial_letter or ssa_policy or agent_inference"
    }
  ]"""


def deadline_schema() -> str:
    return """{
    "notice_date": "YYYY-MM-DD or null",
    "assumed_receipt_date": "YYYY-MM-DD or null",
    "appeal_deadline": "YYYY-MM-DD or null",
    "confidence": 0.0,
    "source": "string",
    "human_review_required": true
  }"""


def mission_schema(mission: str) -> str:
    if mission == "analyze_denial":
        return f"""{{
  "mission": "analyze_denial",
  "denial_summary": "string",
  "denial_reason": "string",
  "ssa_explanation": "string",
  "evidence_mentioned": ["string"],
  "policy_citations": {policy_citation_schema()},
  "human_review_note": "string"
}}"""
    if mission == "find_missing_evidence":
        return f"""{{
  "mission": "find_missing_evidence",
  "case_context": "string",
  "missing_evidence": {missing_evidence_schema()},
  "case_tasks": {case_tasks_schema()},
  "human_review_note": "string"
}}"""
    if mission == "draft_records_request":
        return """{
  "mission": "draft_records_request",
  "request_context": "string",
  "records_needed": ["string"],
  "placeholder_fields": ["string"],
  "records_request_draft": "string",
  "human_review_note": "string"
}"""
    return f"""{{
  "mission": "prepare_review_summary",
  "denial_summary": "string",
  "policy_citations": {policy_citation_schema()},
  "missing_evidence": {missing_evidence_schema()},
  "deadline": {deadline_schema()},
  "case_tasks": {case_tasks_schema()},
  "records_request_draft": "string",
  "review_summary": "string",
  "next_actions": ["string"],
  "human_review_note": "string"
}}"""


def mission_tool_requirements(mission: str) -> str:
    if mission == "analyze_denial":
        return "- Use list_case_documents first.\n- Use list_case_facts after documents.\n- Use search_case_documents for denial reason and uploaded case evidence.\n- Use dignity_search_ssa_policy only for policy needed to explain the denial."
    if mission == "find_missing_evidence":
        return "- Use list_case_documents first.\n- Use list_case_facts after documents.\n- Use search_case_documents for selected case evidence.\n- Use dignity_search_ssa_policy only to understand why a possible evidence gap matters."
    if mission == "draft_records_request":
        return "- Use list_case_documents first.\n- Use list_case_facts after documents and use saved provider facts if present.\n- Use search_case_documents to identify records mentioned by the denial.\n- Use dignity_search_ssa_forms only if needed for SSA-827 or records-release context."
    return "- Use list_case_documents first.\n- Use list_case_facts after documents and prefer saved user facts.\n- Use search_case_documents for denial reason and uploaded case evidence.\n- Use dignity_search_ssa_policy for disability evaluation rules.\n- Use dignity_search_ssa_forms for reconsideration, SSA-827, SSA-561, and appeal workflow if relevant.\n- Use dignity_search_case_memory only if asked about prior saved findings."


def mission_prompt(user_query: str, mission: str, case_id: str) -> str:
    tool_names = DENIAL_TOOL_NAMES if mission == "analyze_denial" else ORCHESTRATOR_TOOL_NAMES
    return f"""
{user_query}

Selected case_id: {case_id}
Analyze only this selected disability denial case.

Mission-specific instruction:
{mission_instructions(mission)}

Tool-name constraints:
{tool_names}

Return ONLY valid JSON. Do not wrap it in Markdown. Do not use ```json fences.
Do not place literal line breaks inside JSON string values. If a letter or draft needs
line breaks, encode them as \\n inside the JSON string.
Escape all quotes inside string values.

Use this exact schema:
{mission_schema(mission)}

Requirements:
- Do not describe the denial as a completed reconsideration denial or as an initial-level denial unless a retrieved document explicitly says that.
{mission_tool_requirements(mission)}
- Use list_case_facts after list_case_documents. Prefer saved user_answer facts over uncertain extracted facts and over model guesses.
- If case_facts.notice_date exists, use it for deadline calculation. If case_facts.provider_name exists, use it in records request context.
- Cite real retrieved doc IDs and policy URLs where available.
- Prefer HTTPS secure.ssa.gov URLs in citations. Do not output http://policy.ssa.gov URLs.
- Say "possible missing evidence" if the record only implies a gap.
- Only return fields in the exact mission schema above.
- For prepare_review_summary only: extract notice date if present, calculate a possible appeal deadline using assumed receipt date plus 60 days, and mark human_review_required true.
- Never claim any deadline is final.
- For find_missing_evidence and prepare_review_summary only: convert each missing-proof gap into a case_tasks item.
- Gemini may only create case_tasks with task_type "missing_proof" and status "suggested"; the backend creates all missing metadata tasks and generated-draft review tasks.
- "Evidence We Reviewed" entries in a denial letter only prove the denial says those records were reviewed; they do not prove the contents, findings, provider opinions, or exam results of those records.
- Do not invent provider names, physical exam findings, normal strength/range-of-motion findings, or doctor statements.
- If doctor records are not present, explicitly say they are missing only in a field allowed by this mission schema.
- Do not give legal advice. State that generated content needs human advocate review.
"""


def event_to_action_logs(event: Any, mission_id: str, case_id: str) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    timestamp = now_iso()
    for call in event.get_function_calls() or []:
        logs.append(
            {
                "event_id": stable_id("event"),
                "case_id": case_id,
                "mission_id": mission_id,
                "event_type": "tool_call",
                "tool_name": call.name,
                "index_name": infer_index_name(call.name),
                "input": call.args or {},
                "output": {},
                "created_at": timestamp,
            }
        )
    for response in event.get_function_responses() or []:
        logs.append(
            {
                "event_id": stable_id("event"),
                "case_id": case_id,
                "mission_id": mission_id,
                "event_type": "tool_result",
                "tool_name": response.name,
                "index_name": infer_index_name(response.name),
                "input": {},
                "output": response.response or {},
                "created_at": timestamp,
            }
        )
    text = as_plain_text(event)
    if event.is_final_response() and text:
        logs.append(
            {
                "event_id": stable_id("event"),
                "case_id": case_id,
                "mission_id": mission_id,
                "event_type": "agent_final_response",
                "tool_name": getattr(event, "author", None) or "dignity_machine",
                "index_name": "action_logs",
                "input": {},
                "output": {"text_preview": text[:2000]},
                "created_at": timestamp,
            }
        )
    return logs


def infer_index_name(tool_name: str) -> str:
    if "ssa_policy" in tool_name:
        return "ssa_policy"
    if "ssa_forms" in tool_name:
        return "ssa_forms"
    if "case_documents" in tool_name or "list_case_documents" in tool_name or "search_case_documents" in tool_name:
        return "case_documents"
    if "case_facts" in tool_name or "list_case_facts" in tool_name:
        return "case_facts"
    if "advocate" in tool_name:
        return "advocate_contacts"
    if "case_memory" in tool_name:
        return "case_facts,evidence_gaps,review_summaries,action_logs,advocate_contacts"
    return ""


async def repair_agent_json(bad_json_text: str, active_runner: Runner) -> str:
    repair_runner = active_runner
    session_id = stable_id("repair_session")
    await session_service.create_session(app_name=repair_runner.app_name, user_id=USER_ID, session_id=session_id)
    repair_prompt = f"""
Convert the following malformed JSON-like text into valid JSON only.

Rules:
- Return only a JSON object.
- Do not use Markdown fences.
- Preserve all keys and meaning.
- Escape raw newlines inside strings as \\n.
- Escape quotes inside strings.
- Do not add commentary.

Malformed text:
{bad_json_text}
"""
    message = types.Content(role="user", parts=[types.Part.from_text(text=repair_prompt)])
    final_text = ""
    async with runner_lock:
        async for event in repair_runner.run_async(user_id=USER_ID, session_id=session_id, new_message=message):
            if event.is_final_response():
                final_text = as_plain_text(event)
    return final_text


def elastic_headers(content_type: str = "application/json") -> dict[str, str]:
    api_key = os.getenv("ELASTIC_API_KEY")
    if not api_key:
        raise RuntimeError("ELASTIC_API_KEY is missing.")
    return {"Authorization": f"ApiKey {api_key}", "Content-Type": content_type}


def elastic_url() -> str:
    value = os.getenv("ELASTIC_URL", "").rstrip("/")
    if not value:
        raise RuntimeError("ELASTIC_URL is missing.")
    return value


def elastic_request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{elastic_url()}{path}",
        data=body,
        headers=elastic_headers(),
        method=method,
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
            return {} if not raw else json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Elastic {method} {path} failed: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Elastic {method} {path} failed: {exc}") from exc


def elastic_bulk(records_by_index: dict[str, list[dict[str, Any]]]) -> None:
    if not records_by_index:
        return
    lines: list[str] = []
    for index_name, records in records_by_index.items():
        for record in records:
            document_id = (
                record.get("gap_id")
                or record.get("fact_id")
                or record.get("update_id")
                or record.get("action_id")
                or record.get("task_id")
                or record.get("deadline_id")
                or record.get("request_id")
                or record.get("summary_id")
                or record.get("packet_id")
                or record.get("event_id")
                or record.get("doc_id")
                or stable_id("doc")
            )
            lines.append(json.dumps({"index": {"_index": index_name, "_id": document_id}}, separators=(",", ":")))
            lines.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    body = ("\n".join(lines) + "\n").encode("utf-8")
    request = Request(
        f"{elastic_url()}/_bulk?refresh=true",
        data=body,
        headers=elastic_headers("application/x-ndjson"),
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Elastic bulk write failed: HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Elastic bulk write failed: {exc}") from exc
    if result.get("errors"):
        failures = [
            item["index"].get("error")
            for item in result.get("items", [])
            if item.get("index", {}).get("error")
        ]
        raise RuntimeError(f"Elastic bulk write had errors: {failures[:3]}")


def log_case_action(case_id: str, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if action_type not in CASE_ACTION_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown action_type: {action_type}")
    action = {
        "action_id": stable_id("action"),
        "case_id": case_id,
        "action_type": action_type,
        "payload": payload or {},
        "created_at": now_iso(),
    }
    elastic_bulk({"case_actions": [action]})
    return action


def save_case_facts(case_id: str, facts: list[CaseFactInput]) -> list[dict[str, Any]]:
    existing = case_fact_map(case_id)
    now = now_iso()
    records: list[dict[str, Any]] = []
    for fact in facts:
        field = re.sub(r"[^a-z0-9_]+", "_", fact.field.lower()).strip("_")
        value = str(fact.value or "").strip()
        if not field or not value:
            continue
        source = fact.source if fact.source in FACT_SOURCES else "user_answer"
        previous = existing.get(field, {})
        records.append(
            {
                "fact_id": previous.get("fact_id") or stable_fact_id(case_id, field),
                "case_id": case_id,
                "field": field,
                "label": fact.label or previous.get("label") or field.replace("_", " ").title(),
                "value": value,
                "source": source,
                "confidence": 1.0 if source == "user_answer" else float(previous.get("confidence", 0.7) or 0.7),
                "created_at": previous.get("created_at") or now,
                "updated_at": now,
            }
        )
    if records:
        elastic_bulk({"case_facts": records})
        log_case_action(case_id, "fact_saved", {"fields": [record["field"] for record in records]})
    return list_case_facts(case_id)


def reset_case_writeback(case_id: str) -> dict[str, int]:
    deleted: dict[str, int] = {}
    query = {"query": {"term": {"case_id": case_id}}}
    for index_name in ("case_tasks", "deadline_tasks", "evidence_gaps", "records_requests", "review_summaries", "appeal_packets", "action_logs"):
        try:
            result = elastic_request_json("POST", f"/{index_name}/_delete_by_query?conflicts=proceed&refresh=true", query)
            deleted[index_name] = int(result.get("deleted", 0))
        except RuntimeError as exc:
            if "index_not_found_exception" not in str(exc) and "HTTP 404" not in str(exc):
                raise
            deleted[index_name] = 0
    return deleted


def build_writeback(structured: dict[str, Any], action_logs: list[dict[str, Any]], case_id: str, mission: str) -> dict[str, list[dict[str, Any]]]:
    created_at = now_iso()
    mission_id = structured["mission_id"]
    mission = canonical_mission(mission)
    tasks: list[dict[str, Any]] = []
    for task in structured.get("case_tasks", []) or []:
        if not isinstance(task, dict):
            continue
        tasks.append(
            {
                "task_id": task.get("task_id") or stable_id("task"),
                "case_id": case_id,
                "mission_id": mission_id,
                "task_type": str(task.get("task_type", "missing_proof")),
                "title": str(task.get("title", "")),
                "description": str(task.get("description", "")),
                "reason": str(task.get("reason", "")),
                "status": str(task.get("status", "ready_for_review")),
                "source": str(task.get("source", "agent_inference")),
                "created_at": created_at,
            }
        )

    deadline = structured.get("deadline") if isinstance(structured.get("deadline"), dict) else {}
    deadline_tasks = []
    if deadline:
        deadline_tasks.append(
            {
                "deadline_id": stable_id("deadline"),
                "case_id": case_id,
                "mission_id": mission_id,
                "notice_date": deadline.get("notice_date"),
                "assumed_receipt_date": deadline.get("assumed_receipt_date"),
                "appeal_deadline": deadline.get("appeal_deadline"),
                "confidence": float(deadline.get("confidence", 0.0) or 0.0),
                "source": deadline.get("source", "agent_inference"),
                "human_review_required": bool(deadline.get("human_review_required", True)),
                "created_at": created_at,
            }
        )

    gaps: list[dict[str, Any]] = []
    for gap in structured.get("missing_evidence", []) or []:
        gaps.append(
            {
                "gap_id": stable_id("gap"),
                "case_id": case_id,
                "mission_id": mission_id,
                "condition": "unknown",
                "gap_type": str(gap.get("gap_type", "possible_missing_evidence")),
                "description": str(gap.get("description", "")),
                "why_it_matters": str(gap.get("why_it_matters", "")),
                "supporting_policy_ids": gap.get("supporting_policy_ids", []) or [],
                "supporting_case_doc_ids": gap.get("supporting_case_doc_ids", []) or [],
                "confidence": float(gap.get("confidence", 0.5) or 0.5),
                "created_at": created_at,
            }
        )

    records_requests: list[dict[str, Any]] = []
    if structured.get("records_request_draft"):
        records_requests.append(
            {
                "request_id": stable_id("request"),
                "case_id": case_id,
                "mission_id": mission_id,
                "status": "draft_for_human_review",
                "request_context": structured.get("request_context", ""),
                "records_needed": structured.get("records_needed", []) or [],
                "placeholder_fields": structured.get("placeholder_fields", []) or [],
                "records_request_text": structured.get("records_request_draft", ""),
                "human_review_note": structured.get("human_review_note", ""),
                "created_at": created_at,
            }
        )

    review_summary = {
        "packet_id": stable_id("packet"),
        "case_id": case_id,
        "mission_id": mission_id,
        "status": "draft_for_human_review",
        "denial_summary": structured.get("denial_summary", ""),
        "policy_citations": structured.get("policy_citations", []) or [],
        "medical_evidence_ids": [
            item.get("doc_id")
            for item in (structured.get("medical_evidence", []) or [])
            if item.get("doc_id")
        ],
        "evidence_gap_ids": [gap["gap_id"] for gap in gaps],
        "records_request_text": structured.get("records_request_draft", ""),
        "advocate_summary": structured.get("advocate_alert_draft", ""),
        "packet_summary": structured.get("review_summary", ""),
        "next_actions": structured.get("next_actions", []) or [],
        "created_at": created_at,
    }

    review_summary_record = {
        "summary_id": stable_id("summary"),
        "case_id": case_id,
        "mission_id": mission_id,
        "status": "draft_for_human_review",
        "denial_summary": structured.get("denial_summary", ""),
        "policy_citations": structured.get("policy_citations", []) or [],
        "missing_evidence": structured.get("missing_evidence", []) or [],
        "deadline": deadline,
        "case_task_ids": [task["task_id"] for task in tasks],
        "records_request_text": structured.get("records_request_draft", ""),
        "review_summary": structured.get("review_summary", ""),
        "next_actions": structured.get("next_actions", []) or [],
        "created_at": created_at,
    }
    writeback_output = {
        "case_task_count": len(tasks) if mission in {"find_missing_evidence", "prepare_review_summary"} else 0,
        "deadline_count": len(deadline_tasks) if mission == "prepare_review_summary" else 0,
        "evidence_gap_count": len(gaps) if mission in {"find_missing_evidence", "prepare_review_summary"} else 0,
        "records_request_count": len(records_requests) if mission in {"draft_records_request", "prepare_review_summary"} else 0,
        "review_summary_count": 1 if mission == "prepare_review_summary" else 0,
        "action_log_count": len(action_logs) + 1,
    }
    if mission == "prepare_review_summary":
        writeback_output["summary_id"] = review_summary_record["summary_id"]

    action_logs.append(
        {
            "event_id": stable_id("event"),
            "case_id": case_id,
            "mission_id": mission_id,
            "event_type": "writeback_prepared",
            "tool_name": "web_app",
            "index_name": "mission_writeback",
            "input": {},
            "output": writeback_output,
            "created_at": created_at,
        }
    )

    if mission == "analyze_denial":
        return {"action_logs": action_logs}
    if mission == "find_missing_evidence":
        return {"evidence_gaps": gaps, "case_tasks": tasks, "action_logs": action_logs}
    if mission == "draft_records_request":
        return {"records_requests": records_requests, "action_logs": action_logs}
    return {
        "case_tasks": tasks,
        "deadline_tasks": deadline_tasks,
        "evidence_gaps": gaps,
        "records_requests": records_requests,
        "review_summaries": [review_summary_record],
        "action_logs": action_logs,
    }


def append_policy_citations(lines: list[str], result: dict[str, Any]) -> None:
    lines.extend(["", "## Policy Citations"])
    citations = result.get("policy_citations", []) or []
    if not citations:
        lines.append("- No policy citations returned.")
        return
    for citation in citations:
        title = citation.get("title") or citation.get("doc_id") or "Policy"
        url = citation.get("url")
        why = citation.get("why_it_matters", "")
        if url:
            lines.append(f"- [{title}]({url}) - {why}")
        else:
            lines.append(f"- **{title}** - {why}")


def append_medical_evidence(lines: list[str], result: dict[str, Any]) -> None:
    lines.extend(["", "## Medical Evidence Found"])
    evidence_items = result.get("medical_evidence", []) or []
    if not evidence_items:
        lines.append("- No medical evidence returned.")
        return
    for evidence in evidence_items:
        lines.append(f"- **{evidence.get('doc_id', 'document')}**: {evidence.get('finding', '')}")


def append_missing_evidence(lines: list[str], result: dict[str, Any]) -> None:
    lines.extend(["", "## Possible Missing Evidence"])
    gaps = result.get("missing_evidence", []) or []
    if not gaps:
        lines.append("- No evidence gaps returned.")
        return
    for gap in result.get("missing_evidence", []) or []:
        lines.append(f"- **{gap.get('gap_type', 'gap')}**: {gap.get('description', '')}")
        if gap.get("why_it_matters"):
            lines.append(f"  - Why it matters: {gap['why_it_matters']}")


def append_action_plan(lines: list[str], result: dict[str, Any]) -> None:
    lines.extend(["", "## Appeal Action Plan"])
    deadline = result.get("deadline") if isinstance(result.get("deadline"), dict) else {}
    if deadline.get("appeal_deadline"):
        lines.append(
            f"- Possible appeal deadline: {deadline.get('appeal_deadline')} "
            f"(human review required; source: {deadline.get('source', 'agent_inference')})"
        )
    else:
        lines.append("- Possible appeal deadline: notice date needed before calculating.")
    tasks = result.get("case_tasks", []) or []
    if tasks:
        for task in tasks:
            if not isinstance(task, dict):
                continue
            lines.append(f"- {task.get('title', 'Task')}: {task.get('description', '')}")
    else:
        lines.append("- No action tasks returned.")


def append_drafts_and_summary(lines: list[str], result: dict[str, Any]) -> None:
    records_request = str(result.get("records_request_draft", "") or "").strip()
    if records_request:
        lines.extend(["", "## Records Request Draft", records_request])

    advocate_alert = str(result.get("advocate_alert_draft", "") or "").strip()
    if advocate_alert:
        lines.extend(["", "## Advocate Alert Draft", advocate_alert])

    packet_summary = str(result.get("packet_summary", "") or "").strip()
    if packet_summary:
        lines.extend(["", "## Review Summary", packet_summary])


def append_writeback(lines: list[str], write_counts: dict[str, int]) -> None:
    lines.extend(["", "## Elastic Writeback"])
    if write_counts:
        for index_name, count in write_counts.items():
            lines.append(f"- `{index_name}`: {count} documents")
    else:
        lines.append("- Disabled for this run. No generated artifacts were written to Elastic.")


def markdown_from_structured(result: dict[str, Any], write_counts: dict[str, int], mission: str) -> str:
    mission = canonical_mission(mission)
    if mission == "analyze_denial":
        lines = ["## Denial Summary", str(result.get("denial_summary", ""))]
        if result.get("denial_reason"):
            lines.extend(["", "## Denial Reason", str(result.get("denial_reason", ""))])
        if result.get("ssa_explanation"):
            lines.extend(["", "## SSA Explanation", str(result.get("ssa_explanation", ""))])
        evidence = result.get("evidence_mentioned", []) or []
        if evidence:
            lines.extend(["", "## Evidence Mentioned"])
            lines.extend(f"- {item}" for item in evidence)
        append_policy_citations(lines, result)
        if result.get("human_review_note"):
            lines.extend(["", "## Human Review", str(result.get("human_review_note", ""))])
        append_writeback(lines, write_counts)
        return "\n".join(lines)

    if mission == "find_missing_evidence":
        lines = ["## Case Context", str(result.get("case_context", ""))]
        append_missing_evidence(lines, result)
        append_action_plan(lines, result)
        if result.get("human_review_note"):
            lines.extend(["", "## Human Review", str(result.get("human_review_note", ""))])
        append_writeback(lines, write_counts)
        return "\n".join(lines)

    if mission == "draft_records_request":
        lines = ["## Request Context", str(result.get("request_context", ""))]
        records_needed = result.get("records_needed", []) or []
        if records_needed:
            lines.extend(["", "## Records Needed"])
            lines.extend(f"- {item}" for item in records_needed)
        placeholders = result.get("placeholder_fields", []) or []
        if placeholders:
            lines.extend(["", "## Placeholder Fields"])
            lines.extend(f"- {item}" for item in placeholders)
        records_request = str(result.get("records_request_draft", "") or "").strip()
        if records_request:
            lines.extend(["", "## Records Request Draft", records_request])
        if result.get("human_review_note"):
            lines.extend(["", "## Human Review", str(result.get("human_review_note", ""))])
        append_writeback(lines, write_counts)
        return "\n".join(lines)

    lines = ["## Denial Summary", str(result.get("denial_summary", ""))]
    append_missing_evidence(lines, result)
    append_action_plan(lines, result)
    append_policy_citations(lines, result)
    records_request = str(result.get("records_request_draft", "") or "").strip()
    if records_request:
        lines.extend(["", "## Records Request Draft", records_request])
    review_summary = str(result.get("review_summary", "") or "").strip()
    if review_summary:
        lines.extend(["", "## Review Summary", review_summary])
    if result.get("human_review_note"):
        lines.extend(["", "## Human Review", str(result.get("human_review_note", ""))])
    append_writeback(lines, write_counts)
    return "\n".join(lines)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/favicon.svg")
def favicon() -> FileResponse:
    return FileResponse(ROOT / "static" / "favicon.svg")


@app.get("/icons.svg")
def icons() -> FileResponse:
    return FileResponse(ROOT / "static" / "icons.svg")


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "default_mission": "prepare_review_summary",
        "missions": [
            {
                "id": "analyze_denial",
                "label": "Explain the denial",
                "description": "Explain why this denial happened.",
            },
            {
                "id": "find_missing_evidence",
                "label": "Find missing proof",
                "description": "Find proof this case still needs.",
            },
            {
                "id": "draft_records_request",
                "label": "Draft doctor records request",
                "description": "Ask doctors for the missing records.",
            },
            {
                "id": "prepare_review_summary",
                "label": "Create review summary",
                "description": "Create a summary for a human helper.",
            },
        ],
        "writeback_default": False,
        "writeback_indexes": ["case_tasks", "deadline_tasks", "evidence_gaps", "records_requests", "review_summaries", "action_logs"],
        "gcp_project": os.getenv("GOOGLE_CLOUD_PROJECT", "integral-tensor-497618-a8"),
    }


@app.post("/api/cases/upload")
async def upload_case(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        data = await file.read()
        return case_service.create_from_pdf(file.filename or "denial.pdf", file.content_type, data)
    except PdfRelevanceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PdfTextExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PdfValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/cases/example")
def use_example_case() -> dict[str, Any]:
    try:
        return case_service.ensure_example_case()
    except (CaseError, PdfTextExtractionError, PdfValidationError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    try:
        return case_service.summary(case_id)
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/cases/{case_id}/facts")
def get_case_facts(case_id: str) -> dict[str, Any]:
    try:
        case_service.summary(case_id)
        return {"case_id": case_id, "facts": list_case_facts(case_id)}
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/cases/{case_id}/facts")
def post_case_facts(case_id: str, payload: CaseFactsRequest) -> dict[str, Any]:
    try:
        case_service.summary(case_id)
        facts = save_case_facts(case_id, payload.facts)
        return {"case_id": case_id, "facts": facts}
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/cases/{case_id}/tasks/{task_id}/status")
def update_case_task_status(case_id: str, task_id: str, payload: TaskStatusRequest) -> dict[str, Any]:
    try:
        case_service.summary(case_id)
        task_type = payload.task_type if payload.task_type in TASK_TYPES else "missing_proof"
        to_status = payload.to_status if payload.to_status in TASK_UPDATE_STATUSES else ""
        if not to_status:
            raise HTTPException(status_code=400, detail=f"Unknown task status: {payload.to_status}")
        update = {
            "update_id": stable_id("task_update"),
            "case_id": case_id,
            "task_id": task_id,
            "task_type": task_type,
            "from_status": "",
            "to_status": to_status,
            "note": payload.note or "",
            "created_at": now_iso(),
        }
        action = {
            "action_id": stable_id("action"),
            "case_id": case_id,
            "action_type": "task_status_updated",
            "payload": {"task_id": task_id, "task_type": task_type, "to_status": to_status, "note": payload.note or ""},
            "created_at": now_iso(),
        }
        elastic_bulk({"case_task_updates": [update], "case_actions": [action]})
        return {"case_id": case_id, "task_id": task_id, "status": to_status, "logged": True}
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/cases/{case_id}/actions/log")
def post_case_action(case_id: str, payload: CaseActionRequest) -> dict[str, Any]:
    try:
        case_service.summary(case_id)
        action = log_case_action(case_id, payload.action_type, payload.payload)
        return {"case_id": case_id, "action": action, "logged": True}
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def make_case_tools(case_id: str):
    def list_case_documents(limit: int = 20) -> dict[str, Any]:
        """List documents for the selected case. The backend applies the case_id filter."""
        return case_store.list_documents(case_id=case_id, limit=limit)

    def search_case_documents(query: str, limit: int = 6) -> dict[str, Any]:
        """Search selected-case documents. The backend applies the case_id filter."""
        return case_store.search_documents(case_id=case_id, query=query, limit=limit)

    def list_case_facts() -> dict[str, Any]:
        """List saved user-provided and agent-extracted facts for the selected case."""
        return {"case_id": case_id, "facts": globals()["list_case_facts"](case_id)}

    return list_case_documents, search_case_documents, list_case_facts


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> StreamingResponse:
    case_id = payload.case_id.strip()
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required.")
    try:
        case_summary = case_service.summary(case_id)
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    classification = case_summary.get("document_classification")
    if isinstance(classification, dict) and classification.get("type") == "irrelevant":
        raise HTTPException(
            status_code=400,
            detail="This selected PDF does not appear to be a denial letter, so Dignity Machine cannot create an appeal action plan from it.",
        )

    if payload.query is not None and payload.query.strip():
        query = payload.query.strip()
        mission = "custom"
    else:
        mission = canonical_mission(payload.mission)
        if mission not in MISSION_QUERIES:
            raise HTTPException(status_code=400, detail=f"Unknown mission: {mission}")
        query = MISSION_QUERIES[mission]

    quick_answer = quick_local_response(query)
    if quick_answer is not None:
        async def quick_stream():
            yield f"data: {json.dumps({'type': 'result', 'answer': quick_answer, 'structured': {'case_id': case_id, 'mode': 'local_quick_response', 'message': quick_answer}, 'mission_id': stable_id('quick'), 'writeback_enabled': False, 'write_counts': {}})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(quick_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    list_tool, search_tool, facts_tool = make_case_tools(case_id)
    root_agent, denial_analyst = build_agents(list_tool, search_tool, facts_tool)
    runner = Runner(app_name=f"{APP_NAME}_{case_id}", agent=root_agent, session_service=session_service)
    denial_runner = Runner(app_name=f"{APP_NAME}_{case_id}_denial", agent=denial_analyst, session_service=session_service)
    active_runner = denial_runner if mission == "analyze_denial" else runner

    async def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Connecting to agent...'})}\n\n"
            mission_id = stable_id("mission")
            final_text = ""
            action_logs: list[dict[str, Any]] = []
            for attempt in range(2):
                session_id = stable_id("session")
                await session_service.create_session(app_name=active_runner.app_name, user_id=USER_ID, session_id=session_id)
                prompt_text = mission_prompt(query, mission, case_id)
                if attempt:
                    prompt_text = (
                        "The previous attempt failed because a tool name was misspelled. "
                        "Use only the exact tool names listed below. Do not call any tool "
                        "whose name is not listed.\n\n"
                        f"{prompt_text}"
                    )
                msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])
                try:
                    async with runner_lock:
                        async for event in active_runner.run_async(user_id=USER_ID, session_id=session_id, new_message=msg):
                            logs = event_to_action_logs(event, mission_id, case_id)
                            action_logs.extend(logs)
                            for log in logs:
                                yield f"data: {json.dumps({'type': 'agent_event', 'event': log})}\n\n"
                            if event.is_final_response():
                                final_text = as_plain_text(event)
                    break
                except ValueError as exc:
                    if attempt == 0 and "Tool '" in str(exc) and "not found" in str(exc):
                        final_text = ""
                        action_logs = []
                        yield f"data: {json.dumps({'type': 'status', 'message': 'Retrying with exact Elastic tool names...'})}\n\n"
                        continue
                    raise
            yield f"data: {json.dumps({'type': 'status', 'message': 'Parsing results...'})}\n\n"
            structured = try_parse_agent_json(final_text)
            if structured is None:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Reformatting output...'})}\n\n"
                repair_text = await repair_agent_json(final_text, active_runner)
                structured = parse_agent_json(repair_text)
            structured = normalize_structured_urls(structured)
            if "medical_evidence" in structured:
                structured = remove_unsupported_medical_evidence(structured, case_id)
            structured = remove_unsupported_generated_case_claims(structured, case_id)
            structured = remove_unavailable_advocate_alert(structured, case_id)
            structured = mission_scoped_structured(structured, mission, case_id)
            structured["case_id"] = case_id
            structured["mission_id"] = mission_id
            action_events = build_action_events(structured, mission_id, case_id, payload.writeback, mission)
            action_logs.extend(action_events)
            for log in action_events:
                yield f"data: {json.dumps({'type': 'agent_event', 'event': log})}\n\n"
            writeback: dict[str, list[dict[str, Any]]] = {}
            if payload.writeback:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Saving action plan to Elastic...'})}\n\n"
                writeback = build_writeback(structured, action_logs, case_id, mission)
                elastic_bulk(writeback)
            write_counts = {k: len(v) for k, v in writeback.items()}
            result_payload = {
                "type": "result",
                "answer": markdown_from_structured(structured, write_counts, mission),
                "structured": structured,
                "mission_id": mission_id,
                "mission": mission,
                "writeback_enabled": payload.writeback,
                "write_counts": write_counts,
            }
            yield f"data: {json.dumps(result_payload)}\n\n"
            yield "data: [DONE]\n\n"
        except HTTPException as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc.detail)})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/cases/{case_id}/writeback/reset")
def reset_writeback(case_id: str) -> dict[str, Any]:
    try:
        case_service.summary(case_id)
        deleted = reset_case_writeback(case_id)
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"case_id": case_id, "deleted": deleted}


@app.get("/api/cases/{case_id}/writeback")
def get_case_writeback(case_id: str) -> dict[str, Any]:
    try:
        case_service.summary(case_id)
        def _search(index: str, size: int = 20) -> list[dict[str, Any]]:
            try:
                result = elastic_request_json(
                    "POST",
                    f"/{index}/_search",
                    {"query": {"term": {"case_id": case_id}}, "sort": [{"created_at": {"order": "desc"}}], "size": size},
                )
            except RuntimeError as exc:
                if "index_not_found_exception" not in str(exc) and "HTTP 404" not in str(exc):
                    raise
                return []
            return [h["_source"] for h in result.get("hits", {}).get("hits", [])]

        return {
            "case_id": case_id,
            "case_facts": _search("case_facts"),
            "case_tasks": _search("case_tasks"),
            "case_task_updates": _search("case_task_updates"),
            "case_actions": _search("case_actions", size=50),
            "deadline_tasks": _search("deadline_tasks", size=5),
            "evidence_gaps": _search("evidence_gaps"),
            "records_requests": _search("records_requests", size=5),
            "review_summaries": _search("review_summaries", size=5),
            "appeal_packets": _search("appeal_packets", size=5),
            "action_logs": _search("action_logs", size=50),
        }
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=3000, reload=False)
