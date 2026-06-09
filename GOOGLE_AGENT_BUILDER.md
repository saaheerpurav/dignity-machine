# Google Agent Builder Connection

Dignity Machine uses Google ADK/Gemini for orchestration and Elastic Agent Builder MCP for global retrieval tools.

## Elastic MCP Endpoint

```text
{KIBANA_URL}/api/agent_builder/mcp
```

Authentication:

```text
Authorization: ApiKey {ELASTIC_API_KEY}
kbn-xsrf: true
```

The current manifest exposes:

- `dignity_search_ssa_policy`
- `dignity_search_ssa_forms`
- `dignity_search_case_documents`
- `dignity_search_case_memory`
- `dignity_get_case_documents`
- `dignity_get_advocate_contact`

The live FastAPI app does not give the agent generic case-document MCP access for selected-case evidence. It builds per-request ADK agents with backend-owned scoped tools:

- `list_case_documents()`
- `search_case_documents(query)`
- `list_case_facts()`

Those functions close over the selected `case_id` and always apply an Elastic `term` filter. `list_case_facts()` lets Gemini use saved user-provided facts such as notice date and provider name without asking again.

## Upload Or Update Tools

```powershell
python scripts/create_agent_builder_tools.py
```

Validate ADK tool discovery:

```powershell
python scripts/test_adk_mcp.py
```

Expected output includes the six MCP tools listed above.

## Local ADK Agent

The ADK agent factory lives in:

```text
dignity_agent/agent.py
```

`build_agents(...)` accepts scoped case-document/fact functions and returns:

- the full orchestrator agent
- the denial-analysis specialist

The app still uses Elastic Agent Builder MCP for global SSA policy/forms/memory/contact retrieval. Selected case evidence and selected case facts are intentionally backend scoped.

Full model execution requires Google model credentials. Use Vertex AI with Application Default Credentials or configure a Gemini API key.

For Vertex AI-backed local runs:

```powershell
$env:GOOGLE_GENAI_USE_VERTEXAI="TRUE"
$env:GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
```

If local Application Default Credentials are missing:

```powershell
gcloud auth application-default login
```

## Deploy Later

Once the agent flow is tested locally:

```powershell
adk deploy agent_engine ^
  --project=your-gcp-project-id ^
  --region=us-central1 ^
  --staging_bucket=gs://your-staging-bucket ^
  --display_name="Dignity Machine" ^
  dignity_agent
```

Do not commit `.env`.
