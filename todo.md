# Dignity Machine TODO

Current state: the app uses one unified case flow. A user selects the bundled example or uploads one text-readable denial PDF, the backend extracts text, stores it in Elastic `case_documents`, and all agent missions run against the selected `case_id` through backend-scoped case tools.

## Verified

- Example denial selection creates/loads a normal preloaded case.
- PDF upload accepts one text-readable PDF and stores extracted denial text in Elastic.
- Scanned or image-only PDFs are rejected before analysis.
- Agent missions require `case_id` and use scoped case-document tools.
- Case document searches apply a backend-owned `case_id` filter.
- Mission buttons run the selected case through Elastic + Gemini.
- Writeback stores generated artifacts with the selected `case_id`.
- Reset deletes generated writeback artifacts for the selected case.
- UI copy no longer presents the example as a separate special mode.

## Remaining

- Add broader automated coverage around malformed PDFs and very large uploads.
- Add a richer document inventory if version 2 supports multiple PDFs per case.
- Add OCR only if the demo scope expands beyond text-readable PDFs.
- Add production authentication and persistence before exposing user case data outside local/demo usage.
