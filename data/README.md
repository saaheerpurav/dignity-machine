# Dignity Machine Data

This folder contains the official SSA/POMS corpus used by Dignity Machine.

## Processed Files

- `processed/ssa_policy.jsonl` - SSA policy chunks for medical evidence, symptoms, RFC, vocational rules, condition guidance, and listings.
- `processed/ssa_forms.jsonl` - SSA appeal, authorization, representation, and form-workflow chunks.
- `processed/scrape_manifest.json` - source-by-source scrape status, chunk counts, source URLs, and raw file paths.

## Runtime Case Data

Uploaded and example case PDFs are not stored as local JSONL seed files. At runtime:

1. FastAPI extracts PDF text with `pypdf`.
2. The text is indexed into Elastic `case_documents`.
3. Each document carries a `case_id`.
4. Agent case tools always search with a hard `case_id` filter.

## Raw Files

`raw/*.html` contains the official SSA/POMS source HTML used to produce the JSONL files.

The public PDF form URLs under `www.ssa.gov/forms/*.pdf` returned `403 Forbidden` from this environment, so the scraper uses equivalent public POMS guidance under `secure.ssa.gov`.

## Ingestion Notes

Each JSONL line is one retrieval chunk. Use `embedding_text` as the semantic-search text field inside Elastic, and keep these fields filterable:

- `source_type`
- `title`
- `url`
- `condition_tags`
- `appeal_stage_tags`
- `chunk_index`

Recommended Elastic indexes:

- `ssa_policy`
- `ssa_forms`
- `case_documents`
- `advocate_contacts`
- `evidence_gaps`
- `appeal_packets`
- `action_logs`

Use `scripts/ingest_elastic.py` from the repo root to validate and ingest policy/form data:

```powershell
python scripts/ingest_elastic.py --dry-run --create-empty-indexes
```

`case_documents` is populated by upload/example API calls, not by local seed files.

Do not treat these records as legal advice. The product should present them as cited policy support for an advocate-ready review packet.
