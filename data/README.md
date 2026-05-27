# Dignity Machine Data

This folder contains the first Elastic corpus for the Dignity Machine hackathon project.

## Processed Files

- `processed/ssa_policy.jsonl` - SSA policy chunks for medical evidence, symptoms, RFC, vocational rules, condition guidance, and listings.
- `processed/ssa_forms.jsonl` - SSA appeal, authorization, representation, and form-workflow chunks.
- `processed/scrape_manifest.json` - Source-by-source scrape status, chunk counts, source URLs, and raw file paths.

## Demo Files

- `demo/maria_case_profile.json` - one-case demo metadata, expected gaps, and intended agent actions.
- `demo/maria_case_documents.jsonl` - synthetic denial letter, medical notes, medication list, symptom journal, work history, function report, and provider list.
- `demo/advocate_contacts.jsonl` - synthetic trusted advocate contact for WhatsApp-style alerts.

The Maria documents are intentionally incomplete. Missing rheumatology records and a missing treating-provider functional-capacity statement are the evidence gaps the agent should detect through Elastic retrieval.

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

For this hackathon, the preferred retrieval path is Elastic hybrid/semantic search through Elastic Agent Builder MCP. External embeddings are optional, not the default.

Use `scripts/ingest_elastic.py` from the repo root to validate and ingest:

```powershell
python scripts/ingest_elastic.py --dry-run --create-empty-indexes
```

Do not treat these records as legal advice. The product should present them as cited policy support for an advocate-ready appeal packet.
