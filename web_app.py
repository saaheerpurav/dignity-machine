from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
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
        "Analyze the selected denial. Find the denial reason, the cited or implied "
        "evidence problems, and the most relevant SSA policy. Keep drafts concise."
    ),
    "find_missing_evidence": (
        "Focus on possible missing evidence in the selected case file. Compare the denial, "
        "case documents, and SSA policy. Identify gaps and explain why each matters."
    ),
    "draft_records_request": (
        "Draft a concise records request for missing medical evidence. "
        "Use case documents, SSA policy, and SSA form guidance. If doctor records "
        "are not present, say they are missing."
    ),
    "prepare_packet": DEFAULT_QUERY,
}
QUICK_RESPONSE = (
    "Hi. This UI is wired for selected-case denial analysis. "
    "Use a mission button to run Gemini with Elastic-backed tools. Short greetings "
    "are answered locally and do not call the agent."
)
DENIAL_TOOL_NAMES = """
Available tools for this mission. Use these exact names only:
- list_case_documents
- search_case_documents
- dignity_search_ssa_policy

Never abbreviate, pluralize, rename, or partially type a tool name. The SSA policy
search tool is exactly dignity_search_ssa_policy.
"""
ORCHESTRATOR_TOOL_NAMES = """
Available tools for this mission. Use these exact names only:
- list_case_documents
- search_case_documents
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
    PdfValidationError,
)
from dignity_agent.agent import build_agents  # noqa: E402


class AnalyzeRequest(BaseModel):
    case_id: str
    mission: str = "prepare_packet"
    query: str | None = None
    writeback: bool = False


class AdvocateAlertRequest(BaseModel):
    case_id: str
    contact_id: str
    message: str
    approved: bool = False


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

    for key in ("denial_summary", "records_request_draft", "packet_summary"):
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
            "This mission is ONLY denial analysis. Focus on denial reason, policy citations, "
            "and evidence referenced by the denial. Keep missing_evidence brief and only "
            "include gaps explicitly stated or strongly implied by the denial. Set "
            "records_request_draft, advocate_alert_draft, and packet_summary to empty strings. "
            "Do not draft letters, alerts, or a full review summary."
        )
    if mission == "find_missing_evidence":
        return (
            "This mission is ONLY evidence-gap analysis. Focus on possible missing evidence "
            "and why each gap matters. Keep denial_summary to one sentence. Include only "
            "policy citations that directly explain why a gap matters. Set "
            "records_request_draft, advocate_alert_draft, and packet_summary to empty strings. "
            "Do not draft letters, alerts, or a full review summary."
        )
    if mission == "draft_records_request":
        return (
            "This mission is records-request drafting. Produce a concise records_request_draft. "
            "Set advocate_alert_draft to an empty string unless an advocate alert is necessary "
            "to explain the request."
        )
    return (
        "This mission is full review-summary preparation. Include denial summary, evidence found, "
        "missing evidence, records request draft, advocate alert draft, review summary, and next actions."
    )


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
{{
  "denial_summary": "string",
  "policy_citations": [
    {{
      "doc_id": "string",
      "chunk_id": "string or null",
      "title": "string",
      "url": "string or null",
      "why_it_matters": "string"
    }}
  ],
  "medical_evidence": [
    {{
      "doc_id": "string",
      "title": "string",
      "finding": "string"
    }}
  ],
  "missing_evidence": [
    {{
      "gap_type": "string",
      "description": "string",
      "why_it_matters": "string",
      "supporting_policy_ids": ["string"],
      "supporting_case_doc_ids": ["string"],
      "confidence": 0.0
    }}
  ],
  "records_request_draft": "string",
  "advocate_alert_draft": "string",
  "packet_summary": "string",
  "next_actions": ["string"]
}}

Requirements:
- Do not describe the denial as a completed reconsideration denial or as an initial-level denial unless a retrieved document explicitly says that.
- Use list_case_documents first.
- Use search_case_documents for denial reason and uploaded case evidence.
- Use dignity_search_ssa_policy for fibromyalgia, symptom evaluation, RFC, and medical opinion rules.
{"" if mission == "analyze_denial" else """- Use dignity_search_ssa_forms for reconsideration, SSA-827, SSA-561, and representative/advocate workflow.
- Use dignity_get_advocate_contact before drafting the advocate alert.
- If dignity_get_advocate_contact returns no contact for this case, set advocate_alert_draft to an empty string.
- Use dignity_search_case_memory if asked about prior saved findings or advocate memory."""}
- Cite real retrieved doc IDs and policy URLs where available.
- Prefer HTTPS secure.ssa.gov URLs in citations. Do not output http://policy.ssa.gov URLs.
- Say "possible missing evidence" if the record only implies a gap.
- The medical_evidence array is only for retrieved case documents whose document_type is medical_record or medication_list.
- Do not put denial_letter PDFs, SSA policy, SSA forms, or assumptions in medical_evidence.
- Every medical_evidence.finding must be directly supported by text returned from search_case_documents.
- "Evidence We Reviewed" entries in a denial letter only prove the denial says those records were reviewed; they do not prove the contents, findings, provider opinions, or exam results of those records.
- Do not invent provider names, physical exam findings, normal strength/range-of-motion findings, or doctor statements.
- If doctor records are not present, set medical_evidence to [] and say they are missing in missing_evidence or next_actions.
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
    if "advocate" in tool_name:
        return "advocate_contacts"
    if "case_memory" in tool_name:
        return "evidence_gaps,appeal_packets,action_logs,advocate_contacts"
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


def reset_case_writeback(case_id: str) -> dict[str, int]:
    deleted: dict[str, int] = {}
    query = {"query": {"term": {"case_id": case_id}}}
    for index_name in ("evidence_gaps", "appeal_packets", "action_logs"):
        result = elastic_request_json("POST", f"/{index_name}/_delete_by_query?conflicts=proceed&refresh=true", query)
        deleted[index_name] = int(result.get("deleted", 0))
    return deleted


def build_writeback(structured: dict[str, Any], action_logs: list[dict[str, Any]], case_id: str) -> dict[str, list[dict[str, Any]]]:
    created_at = now_iso()
    mission_id = structured["mission_id"]
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
        "packet_summary": structured.get("packet_summary", ""),
        "next_actions": structured.get("next_actions", []) or [],
        "created_at": created_at,
    }

    action_logs.append(
        {
            "event_id": stable_id("event"),
            "case_id": case_id,
            "mission_id": mission_id,
            "event_type": "writeback_prepared",
            "tool_name": "web_app",
            "index_name": "evidence_gaps,appeal_packets,action_logs",
            "input": {},
            "output": {
                "evidence_gap_count": len(gaps),
                "packet_id": review_summary["packet_id"],
                "action_log_count": len(action_logs) + 1,
            },
            "created_at": created_at,
        }
    )

    return {
        "evidence_gaps": gaps,
        "appeal_packets": [review_summary],
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
    lines = ["## Denial Summary", str(result.get("denial_summary", ""))]

    if mission == "analyze_denial":
        append_medical_evidence(lines, result)
        append_policy_citations(lines, result)
        gaps = result.get("missing_evidence", []) or []
        if gaps:
            lines.extend(["", "## Denial-Mentioned Evidence Problems"])
            for gap in gaps:
                lines.append(f"- **{gap.get('gap_type', 'issue')}**: {gap.get('description', '')}")
        append_writeback(lines, write_counts)
        return "\n".join(lines)

    if mission == "find_missing_evidence":
        append_missing_evidence(lines, result)
        append_policy_citations(lines, result)
        append_medical_evidence(lines, result)
        append_writeback(lines, write_counts)
        return "\n".join(lines)

    if mission == "draft_records_request":
        append_missing_evidence(lines, result)
        append_policy_citations(lines, result)
        append_drafts_and_summary(lines, result)
        append_writeback(lines, write_counts)
        return "\n".join(lines)

    append_missing_evidence(lines, result)
    append_policy_citations(lines, result)
    append_medical_evidence(lines, result)
    append_drafts_and_summary(lines, result)
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
        "default_mission": "prepare_packet",
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
                "id": "prepare_packet",
                "label": "Create review summary",
                "description": "Create a summary for a human helper.",
            },
        ],
        "writeback_default": False,
        "writeback_indexes": ["evidence_gaps", "appeal_packets", "action_logs"],
        "gcp_project": os.getenv("GOOGLE_CLOUD_PROJECT", "integral-tensor-497618-a8"),
    }


@app.post("/api/cases/upload")
async def upload_case(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        data = await file.read()
        return case_service.create_from_pdf(file.filename or "denial.pdf", file.content_type, data)
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


def make_case_tools(case_id: str):
    def list_case_documents(limit: int = 20) -> dict[str, Any]:
        """List documents for the selected case. The backend applies the case_id filter."""
        return case_store.list_documents(case_id=case_id, limit=limit)

    def search_case_documents(query: str, limit: int = 6) -> dict[str, Any]:
        """Search selected-case documents. The backend applies the case_id filter."""
        return case_store.search_documents(case_id=case_id, query=query, limit=limit)

    return list_case_documents, search_case_documents


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> StreamingResponse:
    case_id = payload.case_id.strip()
    if not case_id:
        raise HTTPException(status_code=400, detail="case_id is required.")
    try:
        case_service.summary(case_id)
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if payload.query is not None and payload.query.strip():
        query = payload.query.strip()
        mission = "custom"
    else:
        mission = payload.mission
        if mission not in MISSION_QUERIES:
            raise HTTPException(status_code=400, detail=f"Unknown mission: {mission}")
        query = MISSION_QUERIES[mission]

    quick_answer = quick_local_response(query)
    if quick_answer is not None:
        async def quick_stream():
            yield f"data: {json.dumps({'type': 'result', 'answer': quick_answer, 'structured': {'case_id': case_id, 'mode': 'local_quick_response', 'message': quick_answer}, 'mission_id': stable_id('quick'), 'writeback_enabled': False, 'write_counts': {}})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(quick_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    list_tool, search_tool = make_case_tools(case_id)
    root_agent, denial_analyst = build_agents(list_tool, search_tool)
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
            structured = remove_unsupported_medical_evidence(structured, case_id)
            structured = remove_unsupported_generated_case_claims(structured, case_id)
            structured = remove_unavailable_advocate_alert(structured, case_id)
            structured["case_id"] = case_id
            structured["mission_id"] = mission_id
            writeback: dict[str, list[dict[str, Any]]] = {}
            if payload.writeback:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Writing artifacts to Elastic...'})}\n\n"
                writeback = build_writeback(structured, action_logs, case_id)
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
            result = elastic_request_json(
                "POST",
                f"/{index}/_search",
                {"query": {"term": {"case_id": case_id}}, "sort": [{"created_at": {"order": "desc"}}], "size": size},
            )
            return [h["_source"] for h in result.get("hits", {}).get("hits", [])]

        return {
            "case_id": case_id,
            "evidence_gaps": _search("evidence_gaps"),
            "appeal_packets": _search("appeal_packets", size=5),
            "action_logs": _search("action_logs", size=50),
        }
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/actions/send-advocate-alert")
async def send_advocate_alert(payload: AdvocateAlertRequest) -> dict[str, Any]:
    if not payload.approved:
        raise HTTPException(status_code=400, detail="Advocate alert requires explicit approval (approved=true).")
    try:
        case_service.summary(payload.case_id)
    except CaseError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_FROM_NUMBER")
    creds_present = all([twilio_sid, twilio_token, twilio_from])
    log_entry: dict[str, Any] = {
        "event_id": stable_id("event"),
        "case_id": payload.case_id,
        "mission_id": "action",
        "event_type": "advocate_alert_approved",
        "tool_name": "twilio_whatsapp",
        "index_name": "action_logs",
        "input": {"contact_id": payload.contact_id, "message_preview": payload.message[:200]},
        "output": {"status": "ready" if creds_present else "pending_credentials"},
        "created_at": now_iso(),
    }
    log_written = True
    try:
        elastic_bulk({"action_logs": [log_entry]})
    except Exception as exc:
        log_written = False
        print(f"[WARN] Failed to write advocate-alert audit log to Elastic: {exc}")
    if not creds_present:
        return {
            "status": "pending_configuration",
            "message": "Alert approved" + (" and logged to Elastic." if log_written else " (Elastic log failed).") + " Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER to .env to enable WhatsApp send.",
            "case_id": payload.case_id,
            "contact_id": payload.contact_id,
            "log_written": log_written,
        }
    return {"status": "ready", "message": "Twilio credentials present. Send pending final implementation.", "case_id": payload.case_id, "log_written": log_written}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=3000, reload=False)
