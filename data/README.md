# Dignity Machine Data

This folder contains the first Elastic corpus for the Dignity Machine hackathon project.

## Processed Files

- `processed/ssa_policy.jsonl` - SSA policy chunks for medical evidence, symptoms, RFC, vocational rules, condition guidance, and listings.
- `processed/ssa_forms.jsonl` - SSA appeal, authorization, representation, and form-workflow chunks.
- `processed/scrape_manifest.json` - Source-by-source scrape status, chunk counts, source URLs, and raw file paths.

## Raw Files

`raw/*.html` contains the official SSA/POMS source HTML used to produce the JSONL files.

The public PDF form URLs under `www.ssa.gov/forms/*.pdf` returned `403 Forbidden` from this environment, so the scraper uses equivalent public POMS guidance under `secure.ssa.gov`.

## Ingestion Notes

Each JSONL line is one retrieval chunk. Use `embedding_text` for semantic embedding, and keep these fields filterable in Elastic:

- `source_type`
- `title`
- `url`
- `condition_tags`
- `appeal_stage_tags`
- `chunk_index`

Recommended Elastic indexes:

- `ssa_policy`
- `ssa_forms`

Do not treat these records as legal advice. The product should present them as cited policy support for an advocate-ready appeal packet.
