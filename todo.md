# Dignity Machine TODO

Current state: the app uses one selected-case flow. A user selects the bundled example or uploads one text-readable denial PDF, the backend extracts text, rejects irrelevant PDFs, stores denial text in Elastic `case_documents`, and all missions run against the selected `case_id` through backend-scoped tools.

The main product is now an in-app agentic workspace: the agent creates mission-specific outputs, asks for missing details, saves user answers to Elastic, updates the action plan, logs task actions, opens Google Calendar deadline drafts, and opens prefilled email drafts.

## Verified By Code Inspection

- Example denial selection creates/loads a normal preloaded case.
- PDF upload accepts one text-readable PDF and stores extracted denial text in Elastic.
- Scanned or image-only PDFs are rejected.
- Irrelevant readable PDFs are rejected before indexing.
- Refresh restore uses `?case=<case_id>` and `GET /api/cases/{case_id}`.
- Agent missions require `case_id`.
- Case document searches apply a backend-owned `case_id` filter.
- Agent receives scoped `list_case_documents`, `search_case_documents`, and `list_case_facts`.
- Mission schemas are separate for explanation, missing proof, records request, and review summary.
- Typed action tasks prevent UI label guessing.
- Notice date is auto-detected from formats such as `Date: June 7, 2026`.
- Saved case facts can drive later reruns.
- Google Calendar and prefilled `mailto:` actions are local user actions, not app-owned external sending.
- Writeback stores generated artifacts and workspace events with the selected `case_id`.

## Must Test Manually

- Example denial full flow.
- Uploaded denial full flow.
- Uploaded denial with no notice date.
- Uploaded denial with `Date: June 7, 2026`.
- Irrelevant PDF rejection.
- Refresh on document preview and app dashboard.
- `analyze_denial` output is explanation-only.
- `find_missing_evidence` output is missing-proof focused.
- `draft_records_request` output is request-focused.
- `prepare_review_summary` output has action plan, deadline, records request, and review summary.
- Save facts, update action plan, and confirm the rerun uses saved facts.
- Mark tasks done/not relevant.
- Add to Google Calendar opens a prefilled event.
- Open email draft opens a prefilled mail client draft.

## Remaining

- Palak will redesign the landing page only.
- The landing page should clearly explain the product, who it is for, the one-PDF flow, the agentic workspace, Elastic's role, and the final actions.
- Keep the main app/dashboard flow unchanged unless explicitly requested.
