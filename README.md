# Dignity Machine

Dignity Machine is a disability-denial evidence agent for the Elastic track. It reads one selected Social Security disability denial PDF, saves extracted text in Elastic, searches official SSA/POMS policy through Elastic Agent Builder MCP, creates mission-specific outputs, and turns the denial into an in-app appeal-prep workspace.

It is not a lawyer, does not guarantee benefits, and does not file anything with SSA.

## Current Product Flow

1. Select the bundled example denial or upload one text-readable denial PDF.
2. The backend extracts text with `pypdf`.
3. A deterministic PDF relevance guardrail rejects readable PDFs that do not look like Social Security disability denial notices.
4. The extracted denial is saved in Elastic `case_documents` with a generated `case_id`.
5. The frontend stores `?case=<case_id>` and restores the selected case on refresh through `GET /api/cases/{case_id}`.
6. Gemini/ADK runs against the selected `case_id`.
7. Case-document and case-fact tools are backend-owned and hard-filtered by `case_id`.
8. SSA policy/forms retrieval uses Elastic Agent Builder MCP.
9. The agent creates mission-specific results instead of one repeated generic report.
10. The app lets the user save missing case facts, update task status, open a Google Calendar deadline draft, and open a prefilled email draft for records requests.

Version 1 supports one text-readable PDF per case and does not perform OCR. Scanned/image-only PDFs are rejected.

## Mission Buttons

- `analyze_denial` - explains what the denial says, why it matters, evidence mentioned, and directly relevant policy citations.
- `find_missing_evidence` - identifies possible missing proof and creates suggested action tasks.
- `draft_records_request` - drafts a doctor/clinic records request and shows placeholder fields.
- `prepare_review_summary` - creates the full appeal action plan, deadline, task list, records request, and review summary.

Each mission has its own schema, prompt, renderer, writeback behavior, and UI surface. Do not collapse them back into one universal output.

## Agentic Workspace

Dignity Machine avoids fake outbound messaging. The agent acts inside the product:

- detects missing case details such as notice date, condition, appeal stage, provider, and denial reason
- asks targeted in-app questions through the Missing Case Details panel
- saves user answers to Elastic `case_facts`
- reruns the action plan using saved facts through `list_case_facts`
- turns evidence gaps into typed action tasks
- lets the user mark tasks done or not relevant
- logs task updates in Elastic
- creates a possible appeal deadline when notice date is known
- opens a Google Calendar event draft for the deadline
- opens a prefilled `mailto:` records request draft without sending from the app
- logs Calendar/mailto actions to Elastic

This is the main agentic demo loop: upload denial, create action plan, fill missing details, save facts, update action plan, then open Calendar/email actions.

## Key Endpoints

- `POST /api/cases/example` creates or returns the bundled example case.
- `POST /api/cases/upload` accepts one PDF and returns a case summary.
- `GET /api/cases/{case_id}` restores a selected case.
- `GET /api/cases/{case_id}/facts` reads saved case facts.
- `POST /api/cases/{case_id}/facts` upserts user-provided facts.
- `POST /api/cases/{case_id}/tasks/{task_id}/status` logs task status changes.
- `POST /api/cases/{case_id}/actions/log` logs workspace actions such as Calendar/mailto openings.
- `POST /api/analyze` runs one mission and requires `case_id`.
- `GET /api/cases/{case_id}/writeback` reads generated artifacts and workspace memory.
- `POST /api/cases/{case_id}/writeback/reset` deletes generated artifacts for one case.

## Elastic Indexes

- `case_documents` - uploaded/example denial text, scoped by `case_id`.
- `case_facts` - user-provided and detected case facts such as notice date and provider name.
- `case_tasks` - generated action tasks.
- `case_task_updates` - task status changes.
- `case_actions` - user actions such as fact save, Calendar open, and mailto open.
- `deadline_tasks` - possible appeal deadline artifacts.
- `records_requests` - generated records request drafts.
- `review_summaries` - generated review summaries.
- `evidence_gaps` - generated missing-evidence artifacts.
- `action_logs` - ADK tool calls, tool results, final response previews, and workspace events.
- `ssa_policy` - official SSA/POMS policy chunks.
- `ssa_forms` - SSA appeal, authorization, representation, and form-workflow chunks.
- `advocate_contacts` - optional legacy/contact index. Current core demo does not depend on WhatsApp/Twilio.

The app path uses scoped backend tools:

- `list_case_documents()`
- `search_case_documents(query)`
- `list_case_facts()`

The generic case-document MCP tools remain available for manual/external use, but the live agent should not rely on them for selected-case evidence.

## Scraped Corpus

Run the SSA/POMS scraper:

```powershell
python scrapers/scrape_ssa.py
```

Outputs:

- `data/raw/*.html`
- `data/processed/ssa_policy.jsonl`
- `data/processed/ssa_forms.jsonl`
- `data/processed/scrape_manifest.json`

Current generated corpus:

- 42 official SSA/POMS source pages
- 168 `ssa_policy` chunks
- 105 `ssa_forms` chunks

## Ingest Into Elastic

Validate local policy/form JSONL without writing:

```powershell
python scripts/ingest_elastic.py --dry-run --create-empty-indexes
```

Ingest with Elastic credentials:

```powershell
$env:ELASTIC_URL="https://YOUR-ELASTIC-ENDPOINT"
$env:ELASTIC_API_KEY="YOUR-API-KEY"
python scripts/ingest_elastic.py --create-empty-indexes
```

By default, ingestion loads `ssa_policy` and `ssa_forms`. Runtime uploads populate `case_documents`; runtime actions populate workflow indexes.

Useful options:

- `--recreate` deletes and recreates selected indexes before ingesting.
- `--index ssa_policy` ingests only one dataset. Repeat `--index` for multiple datasets.
- `--create-empty-indexes` creates empty runtime/workflow indexes such as `case_facts`, `case_tasks`, `deadline_tasks`, `records_requests`, `review_summaries`, `case_actions`, and `action_logs`.

## Agent Builder / ADK

Elastic Agent Builder MCP endpoint:

```text
{KIBANA_URL}/api/agent_builder/mcp
```

Upload Agent Builder tool definitions:

```powershell
python scripts/create_agent_builder_tools.py
```

Validate MCP discovery:

```powershell
python scripts/test_adk_mcp.py
```

Expected MCP tools:

- `dignity_search_ssa_policy`
- `dignity_search_ssa_forms`
- `dignity_search_case_documents`
- `dignity_search_case_memory`
- `dignity_get_case_documents`
- `dignity_get_advocate_contact`

The app uses MCP for global policy/forms/memory/contact tools. Selected case document and case fact search is handled by backend-scoped tools.

## Local App

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the app only when explicitly wanted:

```powershell
python web_app.py
```

Open:

```text
http://127.0.0.1:3000/
```

Frontend source is in `frontend/src`. Build it with:

```powershell
cd frontend
npm run build
```

The build writes the served bundle to `static/`.

Do not commit `.env`.
