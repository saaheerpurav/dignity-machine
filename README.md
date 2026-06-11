# Dignity Machine

**An AI agent that turns a Social Security disability denial letter into a clear appeal-prep workspace.**

Live demo: https://dignity-machine-877261313490.us-central1.run.app

Dignity Machine is built for the **Google Cloud Rapid Agent Hackathon, Elastic track**. It helps a claimant, family member, or advocate understand a disability denial, find the missing proof, connect the denial to official SSA policy, and prepare the next practical actions.

It is not a lawyer, does not guarantee benefits, and does not file anything with SSA.

Most AI document tools stop at summarization. Dignity Machine converts a denial into an evidence-aware action workspace with memory, tasks, policy retrieval, deadline help, and drafts.

## Why This Matters

Social Security disability denial letters are hard to understand. Many people are denied not because their condition is fake, but because the record is incomplete: missing doctor notes, missing functional limits, unclear treatment history, or no treating-source statement.

Dignity Machine makes that problem understandable and actionable:

1. Upload one text-readable Social Security disability denial PDF.
2. The agent extracts the denial reason and important dates.
3. Elastic retrieves relevant SSA/POMS policy and appeal-form guidance.
4. The agent identifies possible missing proof.
5. The app turns the findings into tasks, deadline help, a records request draft, and a review summary.

The goal is simple: **help someone go from "I was denied" to "I know what to do next."**

## What The Judge Should Try

Use the live demo:

```text
https://dignity-machine-877261313490.us-central1.run.app
```

## 30-Second Demo

1. Open the live demo.
2. Click **Use example denial**.
3. Click **Explain the denial**.
4. Click **Find missing proof**.
5. Click **Prepare review summary**.
6. Save a missing detail, rerun the plan, then open the Calendar or email draft actions.

Try either:

- **Use example denial** for the fastest full demo.
- **Upload your own PDF** if it is a text-readable Social Security disability denial letter.

Then run the four core actions:

- **Explain the denial** - plain-English explanation of what SSA said and why it matters.
- **Find missing proof** - evidence gaps and practical next tasks.
- **Draft records request** - a clinic/doctor records request draft.
- **Prepare review summary** - full appeal-prep workspace with tasks, possible deadline, and final summary.

The app also lets the user save missing case details, rerun the plan, mark tasks, open a Google Calendar deadline draft, and open a prefilled local email draft for records requests.

## What Makes It Agentic

Dignity Machine is not just a chatbot response box.

The agent:

- reads the selected denial PDF
- searches official SSA policy and forms through Elastic Agent Builder MCP
- asks for missing details only when needed
- saves user-provided facts to Elastic case memory
- reruns the plan using saved facts
- creates typed action tasks
- logs task updates and workspace actions
- opens user-controlled Calendar and email drafts
- shows an agent trace so judges can see what happened

All selected-case retrieval is backend-scoped by `case_id`, so the agent cannot accidentally analyze the wrong user's document.

## Why This Should Win

Dignity Machine is not a generic document summarizer. It is an agentic workflow for a real, high-friction paperwork problem: Social Security disability denials.

It combines Google ADK/Gemini reasoning, Elastic Agent Builder MCP retrieval over official SSA policy, selected-case memory, missing-evidence detection, task generation, and user-controlled next actions into one working product.

The project is also judge-understandable on first use: one denial letter goes in, and a clear appeal-prep workspace comes out.

## Elastic Usage

Elastic is central to the product, not a checkbox integration.

Dignity Machine uses Elastic for:

- **Official SSA/POMS retrieval** through Elastic Agent Builder MCP
- **SSA forms and appeal workflow search**
- **Uploaded denial storage** in `case_documents`
- **Case facts** such as notice date, condition, provider, and appeal stage
- **Generated tasks, records requests, summaries, and action logs**
- **Traceability** for tool calls and workspace events

The app uses these main indexes:

- `ssa_policy`
- `ssa_forms`
- `case_documents`
- `case_facts`
- `case_tasks`
- `case_task_updates`
- `case_actions`
- `deadline_tasks`
- `records_requests`
- `review_summaries`
- `evidence_gaps`
- `action_logs`

## Google Cloud Usage

Dignity Machine uses:

- **Google ADK** for agent orchestration
- **Gemini on Vertex AI** for reasoning and structured outputs
- **Cloud Run** for the deployed web app
- **Cloud Build** for container deployment

The app is deployed as a single Cloud Run service. FastAPI serves both the backend API and the built React frontend.

## Judging Criteria Alignment

**Technological Implementation**

- Google ADK + Gemini orchestrate mission-specific agents.
- Elastic Agent Builder MCP retrieves official SSA policy and forms.
- Backend-scoped tools enforce selected-case isolation.
- FastAPI streams analysis results and serves the app from Cloud Run.
- Elastic stores both retrieval data and runtime case memory/actions.

**Design**

- The app is built around one understandable workflow: upload denial, understand it, find missing proof, prepare next actions.
- The UI avoids legal jargon where possible and presents results as tasks, drafts, dates, and summaries.
- The judge can use the bundled example or upload a custom denial PDF.

**Potential Impact**

- Disability denials affect people who may already be sick, exhausted, low-income, or without legal help.
- The project targets a real, painful paperwork problem where better understanding can materially change what someone does next.
- It can help claimants, family caregivers, legal aid volunteers, social workers, and disability advocates.

**Quality of Idea**

- Most agents summarize documents. Dignity Machine turns a denial into a guided, evidence-aware action workspace.
- It combines retrieval, case memory, missing-info collection, task generation, and user-controlled next actions.
- The project uses Elastic for semantic policy retrieval and persistent case memory in a way that directly matches the product need.

## Architecture

```text
React frontend
    |
FastAPI backend on Cloud Run
    |
Google ADK / Gemini on Vertex AI
    |
Elastic Agent Builder MCP
    |
Elastic indexes for SSA policy, forms, case documents, facts, tasks, drafts, and logs
```

Important files:

- `web_app.py` - FastAPI app, API routes, mission schemas, ADK runner, streaming responses
- `case_services.py` - PDF extraction, relevance checks, case creation, Elastic case storage
- `dignity_agent/agent.py` - Google ADK agent factory and Elastic MCP wiring
- `frontend/src` - React app source
- `config/elastic_agent_tools.json` - Elastic Agent Builder tool definitions
- `scripts/ingest_elastic.py` - creates Elastic indexes and ingests SSA corpus
- `scripts/create_agent_builder_tools.py` - uploads Elastic Agent Builder tools

## Local Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create `.env`:

```env
ELASTIC_URL=...
ELASTIC_API_KEY=...
KIBANA_URL=...
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=integral-tensor-497618-a8
GOOGLE_CLOUD_LOCATION=us-central1
DIGNITY_AGENT_MODEL=gemini-2.5-flash-lite
```

Ingest Elastic data:

```powershell
python scripts/ingest_elastic.py --create-empty-indexes
python scripts/create_agent_builder_tools.py
python scripts/test_adk_mcp.py
```

Build the frontend:

```powershell
cd frontend
npm install
npm run build
cd ..
```

Run locally:

```powershell
python web_app.py
```

Open:

```text
http://127.0.0.1:3000/
```

## Deployment

The current public deployment is:

```text
https://dignity-machine-877261313490.us-central1.run.app
```

Cloud Run deploy command:

```powershell
gcloud run deploy dignity-machine `
  --source . `
  --project integral-tensor-497618-a8 `
  --region us-central1 `
  --allow-unauthenticated `
  --port 8080 `
  --memory 2Gi `
  --cpu 2 `
  --timeout 300
```

Set secrets and runtime values in Cloud Run environment variables, not in Git.
