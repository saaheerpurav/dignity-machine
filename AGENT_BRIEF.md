# Dignity Machine Agent Brief

This file is context for a future coding agent with no chat history.

## Product

Dignity Machine reads one selected Social Security disability denial PDF, saves extracted text in Elastic, searches SSA/POMS policy through Elastic Agent Builder MCP, identifies possible missing proof, and turns the denial into an in-app appeal-prep workspace.

It is not an AI lawyer, does not guarantee benefits, and does not file directly with SSA.

## Current Architecture

Every case is a normal selected case:

1. User selects the bundled example denial or uploads one text-readable denial PDF.
2. FastAPI extracts text with `pypdf`.
3. A deterministic guardrail rejects irrelevant readable PDFs.
4. The extracted denial is indexed into Elastic `case_documents` with a generated `case_id`.
5. The frontend persists `?case=<case_id>` and restores the case through `GET /api/cases/{case_id}`.
6. `/api/analyze` requires that `case_id`.
7. The backend builds per-request ADK agents with scoped tools.
8. The agent analyzes only the selected case and saved facts for that case.
9. Runtime facts, task updates, workspace actions, generated requests, summaries, and traces are saved to Elastic.

Version 1 supports one text-readable PDF per case. There is no OCR.

## Important Files

- `web_app.py` - FastAPI API, mission prompts/schemas, ADK runner, streaming, normalization, writeback, workspace endpoints.
- `case_services.py` - PDF extraction, relevance classification, case creation, Elastic case storage, scoped case search.
- `dignity_agent/agent.py` - ADK agent factory and MCP/scoped-tool wiring.
- `frontend/src` - React UI source.
- `frontend/src/components/app/MissionResults.tsx` - mission-specific result components.
- `frontend/src/components/app/CaseFactsPanel.tsx` - guided case-completion inputs.
- `frontend/src/components/app/ActionPlan.tsx` - action tasks, Calendar link, task status controls.
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
- `case_facts` - saved user facts and detected facts such as notice date.
- `case_tasks` - generated typed action tasks.
- `case_task_updates` - task status changes.
- `case_actions` - fact save, Calendar open, mailto open, and workspace action events.
- `deadline_tasks` - possible appeal deadline records.
- `records_requests` - records request drafts.
- `review_summaries` - generated review summaries.
- `evidence_gaps` - generated missing-evidence artifacts.
- `action_logs` - ADK tool traces, action events, and audit events.
- `ssa_policy` - global official SSA/POMS policy chunks.
- `ssa_forms` - global SSA forms and appeal workflow chunks.
- `advocate_contacts` - optional legacy/contact index; current core workflow does not depend on WhatsApp/Twilio.

Runtime uploads populate `case_documents`. Runtime user actions populate `case_facts`, `case_task_updates`, and `case_actions`.

## Case Scoping Rule

Do not rely on prompt instructions alone for case scoping.

The live agent must use backend-owned scoped tools:

- `list_case_documents()`
- `search_case_documents(query)`
- `list_case_facts()`

These close over the selected `case_id` and apply backend-controlled Elastic filters. Do not give the live agent a generic case-document MCP tool for selected-case evidence.

SSA policy/forms tools can remain global MCP tools.

## Mission Contracts

Each mission has a distinct schema and UI. Do not add fields that the selected mission does not need.

- `analyze_denial` returns denial explanation, denial reason, SSA explanation, evidence mentioned, policy citations, and human review note.
- `find_missing_evidence` returns case context, missing evidence, typed `missing_proof` tasks, and human review note.
- `draft_records_request` returns request context, records needed, placeholder fields, records request draft, and human review note.
- `prepare_review_summary` returns full review summary, missing evidence, deadline, typed action tasks, records request draft, next actions, and saved case facts.

Legacy `prepare_packet` is mapped to `prepare_review_summary` for compatibility.

## Agentic Workspace

The app does not depend on WhatsApp/Twilio for the core demo. Agentic behavior happens inside the product:

- the agent detects missing details
- the UI asks targeted questions through Missing Case Details
- user answers are saved to Elastic `case_facts`
- the agent reruns using `list_case_facts`
- possible deadlines are calculated from saved or detected notice dates
- user can open a Google Calendar event draft for the possible deadline
- user can open a prefilled local `mailto:` records request draft
- task state changes are logged to Elastic
- agent trace shows tool calls plus workspace events

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
python -m py_compile web_app.py case_services.py dignity_agent\agent.py scripts\ingest_elastic.py
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
- Reject irrelevant readable PDFs before indexing.
- Do not invent provider names, exam findings, or doctor statements.
- If doctor records are not uploaded, say they are missing only in fields allowed by the selected mission schema.
- Use saved user facts over model guesses.
- Notice date priority is saved fact, agent output, then parsed denial text.
- Never claim a deadline is final; always require human review.
- Do not give legal advice.
- Do not push to GitHub unless explicitly asked.

## Next Useful Work

- Manually test the full demo loop after any major change.
- Keep README, AGENT_BRIEF, and parent `dignity_machine.md` synchronized.
- Add regression tests for PDF relevance, scanned PDF rejection, notice-date parsing, mission schemas, and case-fact reruns.
- Decide later whether to add OCR or multi-document upload.
