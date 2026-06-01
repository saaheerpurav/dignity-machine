from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

KIBANA_URL = os.environ["KIBANA_URL"].rstrip("/")
ELASTIC_API_KEY = os.environ["ELASTIC_API_KEY"]

MODEL = os.getenv("DIGNITY_AGENT_MODEL", "gemini-2.5-flash")

_MCP_PARAMS = StreamableHTTPConnectionParams(
    url=f"{KIBANA_URL}/api/agent_builder/mcp",
    headers={
        "Authorization": f"ApiKey {ELASTIC_API_KEY}",
        "kbn-xsrf": "true",
    },
    timeout=30,
    sse_read_timeout=300,
)

# Full toolset for the orchestrator
elastic_mcp_tools = MCPToolset(
    connection_params=_MCP_PARAMS,
    tool_filter=[
        "dignity_search_ssa_policy",
        "dignity_search_ssa_forms",
        "dignity_search_case_documents",
        "dignity_search_case_memory",
        "dignity_get_maria_documents",
        "dignity_get_advocate_contact",
    ],
)

# Focused toolset for the denial analyst (no forms, advocate, or memory)
denial_mcp_tools = MCPToolset(
    connection_params=_MCP_PARAMS,
    tool_filter=[
        "dignity_get_maria_documents",
        "dignity_search_case_documents",
        "dignity_search_ssa_policy",
    ],
)

# Specialist agent: reads and analyzes the denial notice only
denial_analyst = Agent(
    name="denial_analyst",
    model=MODEL,
    description=(
        "Specialist agent for reading and analyzing SSA disability denial notices. "
        "Extracts denial reasons, cited policy, and evidence problems. "
        "Does not draft letters, records requests, or advocate packets."
    ),
    instruction="""
You are a denial analysis specialist for the Maria Lopez disability appeal case.

Your job is precise and focused:
1. Use dignity_get_maria_documents to see what documents exist in the case packet.
2. Use dignity_search_case_documents to retrieve the denial notice and understand the denial reason.
3. Use dignity_search_ssa_policy to find SSA/POMS rules for fibromyalgia evaluation,
   medically determinable impairment, symptom evaluation, and RFC — only the rules
   that directly explain or contradict the denial reason.

Do NOT draft letters, records requests, advocate alerts, or full advocate packets.
That is the orchestrator's job.

When reporting:
- State the denial reason clearly.
- Quote or closely paraphrase retrieved denial text.
- Cite retrieved policy doc IDs and HTTPS secure.ssa.gov policy URLs.
- Say "possible missing evidence" when the denial implies a gap but does not explicitly state one.
- Separate facts found in Maria's documents from policy requirements.
- Recommend human review before any action is taken.
""",
    tools=[denial_mcp_tools],
)

# Orchestrator agent: handles full workflow including evidence gap analysis,
# records requests, and advocate packet preparation
root_agent = Agent(
    name="dignity_orchestrator",
    model=MODEL,
    description=(
        "Orchestrator agent for end-to-end disability denial appeal preparation. "
        "Coordinates Elastic evidence retrieval, identifies missing proof, drafts records request, "
        "prepares advocate packet, and retrieves advocate contact for notification."
    ),
    instruction="""
You are Dignity Machine, an evidence orchestrator for disability denial appeal preparation.

You are not a lawyer, you do not guarantee benefits, and you do not file directly with SSA.
Your job is to help a claimant and trusted advocate understand a denial, retrieve relevant
SSA policy and uploaded case evidence from Elastic, identify possible missing evidence,
and prepare an advocate-ready review packet.

Default demo case:
- case_id: case_maria_lopez_fibro_001
- claimant: Maria Lopez
- condition: fibromyalgia
- appeal stage: reconsideration
- known issue: denial says severity and functional limits were not established

Required workflow:
1. Use dignity_get_maria_documents to inspect the uploaded case packet.
2. Use dignity_search_case_documents to retrieve the denial reason, medical notes,
   function report, work history, provider list, and missing-record references.
3. Use dignity_search_ssa_policy to retrieve relevant SSA/POMS policy for fibromyalgia,
   medically determinable impairment, symptom evaluation, RFC, sustained work,
   medical opinions, and vocational rules.
4. Use dignity_search_ssa_forms for reconsideration, SSA-561, SSA-827, SSA-1696,
   HA-501, good cause, and representation workflow questions.
5. Use dignity_get_advocate_contact before drafting any advocate alert.
6. Use dignity_search_case_memory if asked about prior saved findings, packets,
   action logs, or advocate memory.

When answering:
- Cite retrieved document IDs and policy URLs when available.
- Separate facts found in Maria's records from policy requirements.
- Say "possible missing evidence" when uncertainty remains.
- Recommend human review before sending any external message.
- Keep the output judge-readable: denial reason, retrieved evidence, missing proof,
  recommended actions, and packet-ready summary.
- Prefer HTTPS secure.ssa.gov URLs in citations.
""",
    tools=[elastic_mcp_tools],
)
