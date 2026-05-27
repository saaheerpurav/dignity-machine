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

## Immediate Next

1. Replace the subprocess-based web test endpoint.
   - Current UI calls `adk run` per request, causing slow cold starts.
   - Build an in-process backend runner or a dedicated mission API.
   - Keep agent/toolset initialized once per server process.

2. Create structured mission output.
   - Denial summary.
   - Evidence found.
   - Relevant SSA policy citations.
   - Possible missing evidence.
   - Records request draft.
   - Advocate alert draft.
   - Appeal packet summary.

3. Write generated artifacts back to Elastic.
   - `evidence_gaps`
   - `appeal_packets`
   - `action_logs`

4. Build the real demo UI.
   - Case header: Maria denied for fibromyalgia.
   - Run analysis button.
   - Mission timeline.
   - Elastic evidence cards.
   - Missing evidence section.
   - Records request preview.
   - Advocate alert preview.
   - Appeal packet preview.

5. Add a visible tool trace.
   - Show tool name.
   - Query/input.
   - Elastic index used.
   - Retrieved/written IDs.
   - Short result.

## After That

6. Add human approval flow.
   - User reviews records request.
   - User reviews advocate alert.
   - Nothing external sends without approval.

7. Add notification action.
   - Minimum: local WhatsApp-style simulated alert.
   - Better: real Twilio or WhatsApp Cloud API if credentials are available quickly.

8. Deploy.
   - Cloud Run backend/frontend.
   - Secret Manager for Elastic and Google credentials.
   - Public URL.

9. Submission package.
   - Architecture diagram.
   - 3-minute demo script.
   - Devpost writeup.
   - Final GitHub push only when explicitly requested.

## Do Not Do

- Do not add more scraped data unless the demo needs a specific missing source.
- Do not revive CareOps.
- Do not make Vertex embeddings the default architecture.
- Do not build legal advice or direct SSA filing.
- Do not overbuild the UI before the mission loop and writeback work.
