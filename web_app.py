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

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parent
APP_NAME = "dignity_machine_web"
USER_ID = "local_tester"
CASE_ID = "case_maria_lopez_fibro_001"

DEFAULT_QUERY = (
    "Analyze Maria Lopez's disability denial and prepare the advocate packet. "
    "Use Elastic tools for case documents, SSA policy, SSA forms, and advocate contact."
)
MISSION_QUERIES = {
    "analyze_denial": (
        "Analyze Maria Lopez's denial. Find the denial reason, the cited or implied "
        "evidence problems, and the most relevant SSA policy. Keep drafts concise."
    ),
    "find_missing_evidence": (
        "Focus on possible missing evidence in Maria Lopez's file. Compare the denial, "
        "case documents, and SSA policy. Identify gaps and explain why each matters."
    ),
    "draft_records_request": (
        "Draft a concise records request for Maria Lopez's missing medical evidence. "
        "Use case documents, SSA policy, and SSA form guidance. Include what to ask "
        "Lakeview Rheumatology and the treating provider for."
    ),
    "prepare_packet": DEFAULT_QUERY,
}
QUICK_RESPONSE = (
    "Hi. This test UI is wired for the Maria Lopez denial-analysis mission. "
    "Use the default mission query to run Gemini + Elastic MCP. Short greetings "
    "are answered locally and do not call the agent."
)


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

from dignity_agent.agent import root_agent  # noqa: E402


class AnalyzeRequest(BaseModel):
    mission: str = "prepare_packet"
    query: str | None = None
    writeback: bool = False


app = FastAPI(title="Dignity Machine Test UI")
session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)
runner_lock = asyncio.Lock()


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
            "Do not draft letters, alerts, or a packet."
        )
    if mission == "find_missing_evidence":
        return (
            "This mission is ONLY evidence-gap analysis. Focus on possible missing evidence "
            "and why each gap matters. Keep denial_summary to one sentence. Include only "
            "policy citations that directly explain why a gap matters. Set "
            "records_request_draft, advocate_alert_draft, and packet_summary to empty strings. "
            "Do not draft letters, alerts, or a packet."
        )
    if mission == "draft_records_request":
        return (
            "This mission is records-request drafting. Produce a concise records_request_draft. "
            "Set advocate_alert_draft to an empty string unless an advocate alert is necessary "
            "to explain the request."
        )
    return (
        "This mission is full packet preparation. Include denial summary, evidence found, "
        "missing evidence, records request draft, advocate alert draft, packet summary, and next actions."
    )


def mission_prompt(user_query: str, mission: str) -> str:
    return f"""
{user_query}

Mission-specific instruction:
{mission_instructions(mission)}

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
- The demo workflow stage is reconsideration packet preparation. Do not describe the denial as a completed reconsideration denial or as an initial-level denial unless a retrieved document explicitly says that.
- Use dignity_get_maria_documents first.
- Use dignity_search_case_documents for denial reason and medical evidence.
- Use dignity_search_ssa_policy for fibromyalgia, symptom evaluation, RFC, and medical opinion rules.
- Use dignity_search_ssa_forms for reconsideration, SSA-827, SSA-561, and representative/advocate workflow.
- Use dignity_get_advocate_contact before drafting the advocate alert.
- Cite real retrieved doc IDs and policy URLs where available.
- Prefer HTTPS secure.ssa.gov URLs in citations. Do not output http://policy.ssa.gov URLs.
- Say "possible missing evidence" if the record only implies a gap.
- Do not give legal advice. State that packet content needs human advocate review.
"""


def event_to_action_logs(event: Any, mission_id: str) -> list[dict[str, Any]]:
    logs: list[dict[str, Any]] = []
    timestamp = now_iso()
    for call in event.get_function_calls() or []:
        logs.append(
            {
                "event_id": stable_id("event"),
                "case_id": CASE_ID,
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
                "case_id": CASE_ID,
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
                "case_id": CASE_ID,
                "mission_id": mission_id,
                "event_type": "agent_final_response",
                "tool_name": "dignity_machine",
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
    if "case_documents" in tool_name or "maria_documents" in tool_name:
        return "case_documents"
    if "advocate" in tool_name:
        return "advocate_contacts"
    if "case_memory" in tool_name:
        return "evidence_gaps,appeal_packets,action_logs,advocate_contacts"
    return ""


async def run_agent_in_process(query: str, mission: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    session_id = stable_id("session")
    mission_id = stable_id("mission")
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    message = types.Content(role="user", parts=[types.Part.from_text(text=mission_prompt(query, mission))])
    final_text = ""
    action_logs: list[dict[str, Any]] = []

    async with runner_lock:
        async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=message):
            action_logs.extend(event_to_action_logs(event, mission_id))
            if event.is_final_response():
                final_text = as_plain_text(event)

    structured = try_parse_agent_json(final_text)
    if structured is None:
        repair_text = await repair_agent_json(final_text)
        structured = parse_agent_json(repair_text)
    structured = normalize_structured_urls(structured)
    structured["case_id"] = CASE_ID
    structured["mission_id"] = mission_id
    return structured, action_logs, mission_id


async def repair_agent_json(bad_json_text: str) -> str:
    session_id = stable_id("repair_session")
    await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
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
        async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=message):
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
        f"{elastic_url()}/_bulk",
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


def reset_demo_writeback() -> dict[str, int]:
    deleted: dict[str, int] = {}
    query = {"query": {"term": {"case_id": CASE_ID}}}
    for index_name in ("evidence_gaps", "appeal_packets", "action_logs"):
        result = elastic_request_json("POST", f"/{index_name}/_delete_by_query?conflicts=proceed&refresh=true", query)
        deleted[index_name] = int(result.get("deleted", 0))
    return deleted


def build_writeback(structured: dict[str, Any], action_logs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    created_at = now_iso()
    mission_id = structured["mission_id"]
    gaps: list[dict[str, Any]] = []
    for gap in structured.get("missing_evidence", []) or []:
        gaps.append(
            {
                "gap_id": stable_id("gap"),
                "case_id": CASE_ID,
                "mission_id": mission_id,
                "condition": "fibromyalgia",
                "gap_type": str(gap.get("gap_type", "possible_missing_evidence")),
                "description": str(gap.get("description", "")),
                "why_it_matters": str(gap.get("why_it_matters", "")),
                "supporting_policy_ids": gap.get("supporting_policy_ids", []) or [],
                "supporting_case_doc_ids": gap.get("supporting_case_doc_ids", []) or [],
                "confidence": float(gap.get("confidence", 0.5) or 0.5),
                "created_at": created_at,
            }
        )

    packet = {
        "packet_id": stable_id("packet"),
        "case_id": CASE_ID,
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
            "case_id": CASE_ID,
            "mission_id": mission_id,
            "event_type": "writeback_prepared",
            "tool_name": "web_app",
            "index_name": "evidence_gaps,appeal_packets,action_logs",
            "input": {},
            "output": {
                "evidence_gap_count": len(gaps),
                "packet_id": packet["packet_id"],
                "action_log_count": len(action_logs) + 1,
            },
            "created_at": created_at,
        }
    )

    return {
        "evidence_gaps": gaps,
        "appeal_packets": [packet],
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


def append_drafts_and_packet(lines: list[str], result: dict[str, Any]) -> None:
    records_request = str(result.get("records_request_draft", "") or "").strip()
    if records_request:
        lines.extend(["", "## Records Request Draft", records_request])

    advocate_alert = str(result.get("advocate_alert_draft", "") or "").strip()
    if advocate_alert:
        lines.extend(["", "## Advocate Alert Draft", advocate_alert])

    packet_summary = str(result.get("packet_summary", "") or "").strip()
    if packet_summary:
        lines.extend(["", "## Packet Summary", packet_summary])


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
        append_drafts_and_packet(lines, result)
        append_writeback(lines, write_counts)
        return "\n".join(lines)

    append_missing_evidence(lines, result)
    append_policy_citations(lines, result)
    append_medical_evidence(lines, result)
    append_drafts_and_packet(lines, result)
    append_writeback(lines, write_counts)
    return "\n".join(lines)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "case_id": CASE_ID,
        "default_mission": "prepare_packet",
        "missions": [
            {
                "id": "analyze_denial",
                "label": "Analyze denial",
                "description": "Extract denial reason and supporting SSA policy.",
            },
            {
                "id": "find_missing_evidence",
                "label": "Find missing evidence",
                "description": "Compare Maria's file against policy requirements.",
            },
            {
                "id": "draft_records_request",
                "label": "Draft records request",
                "description": "Prepare provider request language for missing proof.",
            },
            {
                "id": "prepare_packet",
                "label": "Prepare packet",
                "description": "Build the full advocate-ready packet draft.",
            },
        ],
        "writeback_default": False,
        "writeback_indexes": ["evidence_gaps", "appeal_packets", "action_logs"],
        "gcp_project": os.getenv("GOOGLE_CLOUD_PROJECT", "integral-tensor-497618-a8"),
    }


@app.post("/api/analyze")
async def analyze(payload: AnalyzeRequest) -> dict[str, Any]:
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
        return {
            "answer": quick_answer,
            "structured": {
                "case_id": CASE_ID,
                "mode": "local_quick_response",
                "message": quick_answer,
            },
            "mission_id": stable_id("quick"),
            "writeback_enabled": False,
            "write_counts": {},
        }

    try:
        structured, action_logs, mission_id = await run_agent_in_process(query, mission)
        writeback: dict[str, list[dict[str, Any]]] = {}
        if payload.writeback:
            writeback = build_writeback(structured, action_logs)
            elastic_bulk(writeback)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    write_counts = {index_name: len(records) for index_name, records in writeback.items()}
    return {
        "answer": markdown_from_structured(structured, write_counts, mission),
        "structured": structured,
        "mission_id": mission_id,
        "mission": mission,
        "writeback_enabled": payload.writeback,
        "write_counts": write_counts,
    }


@app.post("/api/reset-demo-writeback")
def reset_writeback() -> dict[str, Any]:
    try:
        deleted = reset_demo_writeback()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"case_id": CASE_ID, "deleted": deleted}


@app.get("/api/latest-memory")
def latest_memory() -> dict[str, Any]:
    return {
        "message": "Use Elastic/Kibana to inspect evidence_gaps, appeal_packets, and action_logs.",
        "case_id": CASE_ID,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=3000, reload=False)
