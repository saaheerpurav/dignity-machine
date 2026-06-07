# Dignity Machine

Dignity Machine is a disability-denial evidence agent. It reads one selected denial PDF, saves extracted text in Elastic, searches official SSA/POMS policy, identifies possible missing proof, and builds an advocate-ready review summary.

It is not a lawyer, does not guarantee benefits, and does not file anything with SSA.

## Current Flow

The app treats every case the same way:

1. Select the example denial or upload one text-readable denial PDF.
2. Extract PDF text with `pypdf`.
3. Store the extracted denial in Elastic `case_documents` with a generated `case_id`.
4. Run Gemini/ADK against that selected `case_id`.
5. Case-document tools are backend-owned and always apply a hard Elastic `case_id` filter.
6. SSA policy/forms search remains global through Elastic Agent Builder MCP.
7. Optional writeback saves generated gaps, review summaries, and action logs with the selected `case_id`.

Version 1 supports one PDF per case and does not perform OCR. Scanned/image-only PDFs are rejected.

## Key Endpoints

- `POST /api/cases/example` creates or returns the bundled example case.
- `POST /api/cases/upload` accepts one PDF and returns `{ case_id, title, source_name, extracted_text_preview, document_count }`.
- `POST /api/analyze` requires `case_id`.
- `GET /api/cases/{case_id}/writeback` reads generated artifacts for one case.
- `POST /api/cases/{case_id}/writeback/reset` deletes generated artifacts for one case.

## Elastic Indexes

- `case_documents` - uploaded/example denial text and future case documents, scoped by `case_id`.
- `ssa_policy` - official SSA/POMS policy chunks.
- `ssa_forms` - SSA appeal, authorization, representation, and form-workflow chunks.
- `advocate_contacts` - optional case-scoped advocate contact metadata.
- `evidence_gaps` - generated missing-evidence artifacts.
- `appeal_packets` - generated review summary drafts.
- `action_logs` - tool calls, tool results, final response previews, and writeback audit events.

The live agent does not use the generic case-document MCP search. It receives scoped backend tools:

- `list_case_documents()`
- `search_case_documents(query)`

Both close over the selected `case_id` and add an Elastic `term` filter.

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

By default, ingestion loads only `ssa_policy` and `ssa_forms`. Runtime uploads populate `case_documents`.

Useful options:

- `--recreate` deletes and recreates selected indexes before ingesting.
- `--index ssa_policy` ingests only one dataset. Repeat `--index` for multiple datasets.
- `--create-empty-indexes` also creates `case_documents`, `advocate_contacts`, `evidence_gaps`, `appeal_packets`, and `action_logs`.

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

The app uses MCP for global policy/forms/memory/contact tools. Selected case document search is handled by backend scoped tools.

## Local App

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run the app only when you explicitly want a local server:

```powershell
python web_app.py
```

Open:

```text
http://127.0.0.1:3000/
```

Frontend source is in `frontend/src`. `npm run build` writes the served bundle to `static/`.

Do not commit `.env`.
