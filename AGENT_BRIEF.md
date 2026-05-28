# Dignity Machine Agent Brief

This is the one-shot context file for a new Codex agent with no prior chat history.

## Product

Dignity Machine is an evidence-backed disability denial appeal preparation agent.

One-line pitch:

> Dignity Machine reads a disability denial, searches SSA policy and uploaded medical evidence with Elastic, finds missing proof, and builds an advocate-ready appeal packet.

It is not an AI lawyer. It does not guarantee benefits. It does not file directly with SSA. It prepares a cited packet for claimant/advocate review.

## Hackathon Context

Hackathon: Google Cloud Rapid Agent Hackathon.

Selected partner track: **Elastic**.

Runtime AI story: **Google Cloud Agent Builder / ADK / Gemini**.

Partner integration story: **Elastic Agent Builder MCP**.

Important judging criteria:

- Technological implementation: real Google + partner service integration.
- Design: judge should understand the workflow immediately.
- Potential impact: meaningful real-world problem.
- Quality of idea: creative, unique, agentic, not a chatbot.

The project should demonstrate an agent that acts:

1. Extracts denial reason.
2. Searches Elastic for SSA policy.
3. Searches Elastic for claimant records.
4. Identifies possible missing evidence.
5. Drafts records request / packet content.
6. Gets advocate contact.
7. Saves generated artifacts back to Elastic.

## Demo Story

Use one polished demo case:

> Maria Lopez was denied disability benefits for fibromyalgia. SSA said the record did not establish severity and functional limitations. Dignity Machine searches official SSA/POMS policy and Maria's uploaded records, finds missing rheumatology records and a missing treating-provider functional capacity statement, drafts a records request, prepares an advocate packet, and alerts her trusted advocate for review.

The judge should understand this in one sentence:

> Maria was denied. The agent found why, found the missing proof, and prepared an advocate packet grounded in SSA policy.

## Current Working State

The following is already working:

- Official SSA/POMS corpus scraped.
- Maria Lopez synthetic demo case created.
- Data ingested into Elastic.
- Elastic Agent Builder tools created.
- Elastic MCP endpoint verified.
- ADK/Gemini agent connected to Elastic MCP.
- Local ADK smoke test works against Vertex AI project `integral-tensor-497618-a8`.
- Minimal local web UI exists for testing only.
- Web UI now uses an in-process ADK runner, requests structured JSON, and renders Markdown.
- Generated gaps/packets/action logs can be written back to Elastic, but writeback is optional and disabled by default for casual testing.
- Temporary frontend lives in `static/index.html`; backend API logic lives in `web_app.py`.
- UI uses fixed mission buttons instead of freeform chat. Every real mission is a live run; no cache is used.

Do not redo the data scrape or tool creation unless something is broken.

## Repository Map

Important files:

- `README.md` - repo-level setup and commands.
- `todo.md` - current remaining engineering tasks.
- `GOOGLE_AGENT_BUILDER.md` - ADK / Vertex / Elastic MCP connection notes.
- `dignity_agent/agent.py` - ADK Gemini agent connected to Elastic MCP.
- `web_app.py` - minimal local test web UI, temporary.
- `requirements.txt` - Python dependencies.
- `scrapers/scrape_ssa.py` - official SSA scraper.
- `scripts/ingest_elastic.py` - creates Elastic indexes and ingests data.
- `scripts/create_agent_builder_tools.py` - creates Elastic Agent Builder tools.
- `scripts/test_adk_mcp.py` - verifies ADK can discover Elastic MCP tools.
- `config/elastic_agent_tools.json` - Elastic Agent Builder tool definitions.
- `data/processed/ssa_policy.jsonl` - official SSA policy chunks.
- `data/processed/ssa_forms.jsonl` - official SSA forms/appeals chunks.
- `data/demo/maria_case_documents.jsonl` - synthetic claimant packet.
- `data/demo/advocate_contacts.jsonl` - synthetic advocate contact.
- `data/demo/maria_case_profile.json` - demo case metadata.

Do not commit `.env`.

## Elastic Indexes

Loaded indexes:

- `ssa_policy` - official SSA/POMS policy chunks.
- `ssa_forms` - official SSA form and appeal workflow chunks.
- `case_documents` - Maria's synthetic denial, medical notes, function report, work history, etc.
- `advocate_contacts` - Elena Lopez trusted advocate contact.

Empty writeback indexes:

- `evidence_gaps`
- `appeal_packets`
- `action_logs`

Expected loaded counts:

- `ssa_policy`: 168
- `ssa_forms`: 105
- `case_documents`: 8
- `advocate_contacts`: 1

## Elastic MCP Tools

Created in Elastic Agent Builder:

- `dignity_search_ssa_policy`
- `dignity_search_ssa_forms`
- `dignity_search_case_documents`
- `dignity_search_case_memory`
- `dignity_get_maria_documents`
- `dignity_get_advocate_contact`

Local manifest names use dots, but MCP exposes underscores:

- manifest: `dignity.search_ssa_policy`
- MCP: `dignity_search_ssa_policy`

Verify tool discovery:

```powershell
python scripts/test_adk_mcp.py
```

Expected output:

```text
adk_mcp_tool_count=6
dignity_search_ssa_policy
dignity_search_ssa_forms
dignity_search_case_documents
dignity_search_case_memory
dignity_get_maria_documents
dignity_get_advocate_contact
```

## Google / Vertex State

Use GCP project:

```text
integral-tensor-497618-a8
```

Do not use the older project `durable-height-427320-e6`.

For local ADK/Vertex runs:

```powershell
$env:GOOGLE_GENAI_USE_VERTEXAI="TRUE"
$env:GOOGLE_CLOUD_PROJECT="integral-tensor-497618-a8"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
```

If ADC fails:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project integral-tensor-497618-a8
```

## Local Test Commands

Install dependencies:

```powershell
pip install -r requirements.txt
```

Test Elastic MCP discovery:

```powershell
python scripts/test_adk_mcp.py
```

Run ADK agent directly:

```powershell
$env:GOOGLE_GENAI_USE_VERTEXAI="TRUE"
$env:GOOGLE_CLOUD_PROJECT="integral-tensor-497618-a8"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
adk run dignity_agent "Analyze Maria Lopez's denial. Use Elastic tools to find the denial reason, relevant SSA policy, missing evidence, and what should go into the advocate packet." --in_memory --timeout 180s
```

Run minimal local web UI:

```powershell
python web_app.py
```

Open:

```text
http://127.0.0.1:3000/
```

The current web UI is intentionally temporary. It uses an in-process ADK runner and can perform real Elastic writeback when the checkbox is enabled, but it is not the final judge-facing UI.
It has fixed mission buttons and a simulated progress timeline so short greetings do not trigger full agent missions.

## Immediate Build Priority

Build the real minimal product workflow around the working agent.

Do not add more scraped data yet. Do not create a big dashboard. Do not over-design.

Priority order:

1. Harden the `web_app.py` in-process backend runner and add streaming progress.
2. Improve structured mission output:
   - denial summary
   - policy citations
   - medical evidence found
   - possible missing evidence
   - records request draft
   - advocate alert draft
   - packet summary
3. Improve generated artifact writeback to Elastic:
   - `evidence_gaps`
   - `appeal_packets`
   - `action_logs`
   - show written document IDs in the UI
   - keep writeback opt-in during testing to avoid clutter
4. Build judge-readable UI:
   - case header
   - run analysis button
   - mission timeline
   - Elastic evidence cards
   - missing evidence section
   - records request preview
   - advocate alert preview
   - appeal packet preview
5. Add human approval before any external notification.

## UI Direction

The UI should be simple and story-first.

Recommended first screen:

- Title: `Maria was denied disability benefits. Dignity Machine found what evidence is missing.`
- Button: `Analyze denial`
- Timeline:
  1. Denial read
  2. SSA policy searched
  3. Medical records searched
  4. Missing evidence found
  5. Records request drafted
  6. Advocate packet ready
- Evidence cards:
  - show source/index/doc ID
  - show short excerpt
  - show why it matters
- Packet preview:
  - denial reason
  - policy support
  - missing evidence checklist
  - draft request
  - advocate alert

Avoid a dense legal dashboard. Judges should understand the project in 30 seconds.

## What Must Be Real

- Elastic retrieval must be real.
- Elastic MCP tool calls must be real.
- Evidence cards must come from indexed documents.
- Generated packet must cite retrieved doc IDs / URLs.
- Writeback to Elastic must be real for final demo.
- Gemini / Google ADK must be the runtime agent story.

Seeded demo claimant data is acceptable because it is transparently indexed and retrieved.

## What Not To Build

- Do not revive CareOps.
- Do not build an AI lawyer.
- Do not claim the agent wins appeals.
- Do not file directly with SSA.
- Do not build ALJ judge ranking.
- Do not add benefit calculators.
- Do not make Vertex embeddings the default architecture.
- Do not fake tool calls or hardcode final packet content.
- Do not push to GitHub unless the user explicitly asks.

## Current Git Policy

The user explicitly said:

> do not push to github always, only do when i tell you

So make local changes as requested, but only push when explicitly told.

## Current Best Next Task

Build a real but still minimal web workflow:

```text
Analyze Maria -> stream/display mission steps -> show Elastic evidence -> show missing evidence -> show packet draft -> save artifacts to Elastic
```

The technical foundation is already strong. The winning gap is the judge-facing product experience.

Do not turn this into a freeform chat UI. The product should feel like mission execution with explicit actions.
