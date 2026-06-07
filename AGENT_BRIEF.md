# Dignity Machine Agent Brief

This file is context for a future coding agent with no chat history.

## Product

Dignity Machine reads one selected disability denial PDF, saves extracted text in Elastic, searches SSA/POMS policy, identifies possible missing proof, and builds an advocate-ready review summary.

It is not an AI lawyer, does not guarantee benefits, and does not file directly with SSA.

## Current Architecture

Every case is a normal case:

1. User selects the bundled example denial or uploads one text-readable denial PDF.
2. FastAPI extracts text with `pypdf`.
3. The extracted denial is indexed into Elastic `case_documents` with a generated `case_id`.
4. `/api/analyze` requires that `case_id`.
5. The backend builds per-request ADK agents with scoped case tools.
6. The agent analyzes only the selected case.
7. Optional writeback stores generated artifacts with the selected `case_id`.

Version 1 supports one text-readable PDF per case. There is no OCR.

## Important Files

- `web_app.py` - FastAPI API, ADK runner, prompts, streaming, writeback.
- `case_services.py` - PDF extraction, case creation, Elastic case storage, scoped case search.
- `dignity_agent/agent.py` - ADK agent factory.
- `frontend/src` - React UI source.
- `static` - built frontend served by FastAPI.
- `config/elastic_agent_tools.json` - Elastic Agent Builder manifest.
- `scripts/ingest_elastic.py` - creates indexes and ingests policy/form corpora.
- `scripts/create_agent_builder_tools.py` - uploads Agent Builder tools.
- `scripts/test_adk_mcp.py` - verifies MCP tool discovery.
- `data/processed/ssa_policy.jsonl` - official SSA/POMS policy chunks.
- `data/processed/ssa_forms.jsonl` - official SSA appeal/form chunks.

Do not commit `.env`.

## Elastic Indexes

- `case_documents` - uploaded/example case documents, scoped by `case_id`.
- `ssa_policy` - global official SSA/POMS policy chunks.
- `ssa_forms` - global SSA forms and appeal workflow chunks.
- `advocate_contacts` - optional case-scoped advocate contacts.
- `evidence_gaps` - generated writeback.
- `appeal_packets` - generated review summary drafts.
- `action_logs` - tool traces and audit events.

Runtime uploads populate `case_documents`. Local seed case JSONL files have been removed.

## Case Scoping Rule

Do not rely on prompt instructions alone for case scoping.

The live agent must use backend-owned case tools:

- `list_case_documents()`
- `search_case_documents(query)`

These close over the selected `case_id` and apply an Elastic `term` filter. Do not give the live agent a generic case-document MCP tool for selected-case evidence.

SSA policy/forms tools can remain global MCP tools.

## Current MCP Tools

Elastic Agent Builder exposes:

- `dignity_search_ssa_policy`
- `dignity_search_ssa_forms`
- `dignity_search_case_documents`
- `dignity_search_case_memory`
- `dignity_get_case_documents`
- `dignity_get_advocate_contact`

The generic case-document tools are kept for external/manual use. The app path uses scoped backend functions.

## Local Commands

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Validate Python files:

```powershell
python -m py_compile web_app.py case_services.py dignity_agent\agent.py
```

Build frontend:

```powershell
cd frontend
npm run build
```

Validate Elastic MCP discovery:

```powershell
python scripts/test_adk_mcp.py
```

Upload Agent Builder tools:

```powershell
python scripts/create_agent_builder_tools.py
```

Run the app only when explicitly requested:

```powershell
python web_app.py
```

## Guardrails

- Never present a denial letter as a doctor record.
- Do not invent provider names, exam findings, or doctor statements.
- If doctor records are not uploaded, say they are missing.
- Do not give legal advice.
- Recommend human review before any external message.
- Do not push to GitHub unless explicitly asked.

## Next Useful Work

- Add regression tests for PDF upload, scanned PDF rejection, required `case_id`, and medical-evidence filtering.
- Add UI display for backend warnings such as removed unsupported medical evidence.
- Decide whether old indexed seed case documents should be deleted from the live Elastic cluster.
