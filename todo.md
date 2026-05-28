# Dignity Machine TODO

Current state: data, Elastic, Elastic MCP tools, and local ADK/Gemini agent are working. The minimal web UI exists only for testing and should be replaced.

## Done

- Scraped official SSA/POMS corpus.
- Created Maria Lopez synthetic demo case.
- Ingested data into Elastic indexes.
- Created Elastic Agent Builder tools.
- Verified Elastic MCP endpoint.
- Built ADK/Gemini agent connected to Elastic MCP.
- Verified end-to-end local agent call with Vertex AI project `integral-tensor-497618-a8`.
- Added minimal local test UI at `http://127.0.0.1:3000/`.
- Replaced subprocess-based web endpoint with in-process ADK runner.
- Added structured mission output and Elastic writeback for gaps, packets, and action logs.
- Split temporary frontend into `static/index.html` so UI work does not require backend edits.
- Made Elastic writeback optional and disabled by default.
- Added demo writeback reset endpoint.
- Replaced freeform chat box with fixed mission buttons.
- Added immediate progress timeline for long live agent runs.
- Manually tested the four mission buttons in the browser.
- Hardened JSON parsing for draft-generation failures, including malformed fenced JSON and raw control characters.

## Owner Split

### Palak - Frontend

Goal: replace the temporary test page with the judge-facing demo UI. Do not change backend/agent logic unless a backend owner gives you a specific API contract change.

Design direction:

- Light theme only.
- Overall feel: calm, credible, civic/advocacy tool; not a dark SaaS dashboard and not a medical emergency app.
- Use a clean white / off-white background with restrained teal/blue accents.
- Avoid gradients, dark panels, decorative blobs, and oversized marketing hero sections.
- Palak will also design a separate landing page. The main Dignity Machine app/workflow should live inside the product after the landing page entry point.
- Landing page should be simple and credible:
  - Explain the product quickly.
  - Show the offer: turn a disability denial into an advocate-ready evidence packet.
  - Include a clear CTA into the Maria demo app.
  - Do not overdo marketing copy or abstract AI claims.
- Main app first screen must be immediately understandable:
  - Maria was denied.
  - The agent is finding missing evidence.
  - Elastic-backed evidence and actions are visible.
- Use cards only for individual evidence items, missing-evidence items, packet sections, and tool events.
- Do not put cards inside cards.
- Keep typography compact and readable; no giant hero text inside the app.
- Buttons should be clear actions with short labels.
- Use badges/pills for source type, index name, confidence, and status.
- Use a vertical or horizontal mission timeline with obvious active/done states.
- The technical trace should be visually secondary.
- Mobile should stack sections cleanly; do not hide the core story on mobile.
- Desktop demo is priority, but mobile must not break.
- The UI should look credible enough for a government/legal aid workflow.
- Avoid anything that looks like a generic AI chat template.

Tasks:

1. Build the real demo UI in the frontend layer.
   - Case header: Maria denied for fibromyalgia.
   - Four mission buttons:
     - Analyze denial
     - Find missing evidence
     - Draft records request
     - Prepare packet
   - Main story timeline.
   - Elastic evidence cards.
   - Missing evidence checklist.
   - Records request preview.
   - Advocate alert preview.
   - Appeal packet preview.
   - Writeback status panel showing saved Elastic IDs.

2. Replace the Markdown block with structured sections/cards.
   - Use backend fields:
     - `denial_summary`
     - `policy_citations`
     - `medical_evidence`
     - `missing_evidence`
     - `records_request_draft`
     - `advocate_alert_draft`
     - `packet_summary`
     - `next_actions`
   - Keep policy citations clickable.
   - Make missing evidence easy to scan.

3. Build the technical trace panel.
   - Secondary/right-side panel, not the main story.
   - Show:
     - tool name
     - query/input
     - Elastic index used
     - retrieved/written IDs
     - short result
   - Keep it compact so judges are not overwhelmed.

4. Add human approval UI.
   - User reviews records request.
   - User reviews advocate alert.
   - User explicitly approves before Twilio send.

5. Keep the UI mission-based, not chat-based.
   - Do not add a freeform chatbot as the primary interface.
   - The product should feel like mission execution with clear actions.

Frontend guardrails:

- The app is not a chatbot. It is a case mission dashboard.
- First screen must explain the whole product in 10 seconds.
- Prioritize story order:
  1. Maria was denied.
  2. Agent found why.
  3. Elastic found policy/evidence.
  4. Missing proof identified.
  5. Packet prepared for advocate review.
- Make the `Prepare packet` output feel like the final payoff.
- Keep technical trace visible but secondary.
- Use real document IDs/source labels in evidence cards.
- Do not hide citations behind generic "sources".
- Make empty/loading/error states polished.
- Make writeback status obvious: preview vs saved to Elastic.

### Supreet - Backend, Agent, Elastic, Twilio

Goal: make the API production-shaped for the final UI and add the real action layer.

Tasks:

1. Add real mission event streaming.
   - Add `GET /api/missions/{mission_id}/events` or SSE equivalent.
   - Stream actual ADK events from `runner.run_async`.
   - Emit:
     - `tool_call`
     - `tool_result`
     - `agent_final_response`
     - `writeback_complete`
   - Include tool name, index name, input/query, retrieved/written IDs when available.
   - Replace the frontend's simulated timeline with these backend events.

2. Return stable structured data for the final UI.
   - Keep `/api/analyze` returning `answer` Markdown for the temporary UI if useful.
   - Also return:
     - `denial_summary`
     - `policy_citations`
     - `medical_evidence`
     - `missing_evidence`
     - `records_request_draft`
     - `advocate_alert_draft`
     - `packet_summary`
     - `next_actions`
   - When writeback is enabled, return:
     - `packet_id`
     - `gap_ids`
     - `action_log_ids`

3. Expose writeback results clearly.
   - Current endpoint writes to `evidence_gaps`, `appeal_packets`, and `action_logs` only when `writeback=true`.
   - Return exact written document IDs in `/api/analyze`.
   - Add `GET /api/cases/{case_id}/writeback` to read latest gaps, packet, and logs from Elastic.
   - Keep `POST /api/reset-demo-writeback` for local testing.

4. Add Twilio WhatsApp action.
   - Use Twilio for WhatsApp; Saaheer already has a Twilio number.
   - Add env vars for Twilio credentials and sender number.
   - Add backend endpoint:
     - `POST /api/actions/send-advocate-alert`
   - Input should include:
     - `case_id`
     - `contact_id`
     - approved message text
   - Do not send unless frontend passes explicit approval.
   - Log Twilio send attempt/result to `action_logs`.

5. Add Twilio webhook endpoint if time allows.
   - `POST /api/whatsapp/webhook`
   - Store inbound advocate replies in Elastic `action_logs` or a new `messages` index.
   - This is optional for MVP if outbound Twilio alert works.

6. Keep Elastic clean during testing.
   - Keep writeback disabled by default.
   - Keep reset endpoint working.
   - Do not write on preview runs.

Backend guardrails:

- Keep frontend API stable; do not make frontend work chase backend changes.
- Define clear response schemas for each mission.
- Add real SSE events before adding more features.
- Return exact written Elastic IDs after writeback.
- Build `GET /api/cases/{case_id}/writeback`.
- Add Twilio send only after an explicit approval flag is passed.
- Log all Twilio attempts/results to `action_logs`.
- Never write to Elastic unless `writeback=true`.
- Keep reset endpoint safe and scoped to Maria demo case only.
- Do not add more agent tools unless needed by UI/demo.
- Keep all secrets in env vars, never code.
- Make errors frontend-readable, not giant stack traces.
- Add one smoke-test script for:
  - Elastic MCP discovery.
  - mission run.
  - writeback off.
  - writeback on.
  - reset endpoint.

### Saaheer - Deployment, Submission, Coordination

Goal: get the final build hosted and submission-ready.

Tasks:

1. Deployment.
   - Deploy backend/frontend to Cloud Run.
   - Configure env vars / Secret Manager:
     - Elastic URL/API key
     - Kibana URL if needed
     - Google project/location
     - Twilio credentials
   - Verify public URL works.

2. Final integration check.
   - Confirm Elastic MCP tools work after deployment.
   - Confirm mission buttons run on deployed URL.
   - Confirm writeback works only when enabled.
   - Confirm reset works.
   - Confirm Twilio WhatsApp send works after approval.

3. Submission assets.
   - Architecture diagram.
   - 3-minute demo script.
   - Devpost writeup.
   - Demo video.
   - Final GitHub push only when ready.

4. Judge story.
   - Keep the explanation simple:
     - Maria was denied.
     - The agent found why.
     - Elastic found policy and evidence.
     - The agent found missing proof.
     - The agent prepared an advocate packet.
     - Human approves before anything is sent.

## Do Not Do

- Do not add more scraped data unless the demo needs a specific missing source.
- Do not revive CareOps.
- Do not make Vertex embeddings the default architecture.
- Do not build legal advice or direct SSA filing.
- Do not make the primary UI a chatbot.
- Do not send WhatsApp messages without explicit user approval.
- Do not push to GitHub unless explicitly requested.

## Shared Demo Rule

Do not optimize for a complete platform. Optimize for a clean 3-minute demo where every action is understandable and real.
