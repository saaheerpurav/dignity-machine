# Google Agent Builder Connection

Dignity Machine uses the Vertex AI Agent Builder path through ADK:

- Gemini model orchestration through Google ADK / Vertex AI Agent Builder.
- Elastic Agent Builder MCP as the partner MCP server.
- Elastic indexes as the evidence and memory layer.

## Elastic MCP Endpoint

The Elastic MCP endpoint is:

```text
{KIBANA_URL}/api/agent_builder/mcp
```

Authentication:

```text
Authorization: ApiKey {ELASTIC_API_KEY}
kbn-xsrf: true
```

The endpoint has been smoke-tested with the MCP `initialize` and `tools/list` methods. It exposes:

- `dignity_search_ssa_policy`
- `dignity_search_ssa_forms`
- `dignity_search_case_documents`
- `dignity_search_case_memory`
- `dignity_get_maria_documents`
- `dignity_get_advocate_contact`

Verified locally:

```text
adk_mcp_tool_count=6
```

## Local ADK Agent

The ADK agent lives in:

```text
dignity_agent/agent.py
```

It loads `.env`, connects to Elastic MCP, filters to the six Dignity Machine tools, and defines the Maria Lopez workflow prompt.

Validate ADK tool discovery:

```powershell
python scripts/test_adk_mcp.py
```

Run locally with ADK after Google auth/model credentials are configured:

```powershell
adk run dignity_agent
```

Current blocker for a full Gemini run:

- Elastic MCP discovery works.
- Vertex AI API is enabled on the current GCP project.
- Local ADK model execution still needs either Application Default Credentials or a Gemini API key.

The attempted Vertex run failed with missing local ADC. To fix that, run:

```powershell
gcloud auth application-default login
```

Then run:

```powershell
$env:GOOGLE_GENAI_USE_VERTEXAI="TRUE"
$env:GOOGLE_CLOUD_PROJECT="integral-tensor-497618-a8"
$env:GOOGLE_CLOUD_LOCATION="us-central1"
adk run dignity_agent "List the Maria demo documents using the Elastic MCP tool, then summarize the denial in one sentence." --in_memory --timeout 90s
```

For Vertex AI-backed local runs, set:

```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

If local Application Default Credentials are missing, run:

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
