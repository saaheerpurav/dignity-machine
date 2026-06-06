from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

KIBANA_URL = os.environ["KIBANA_URL"].rstrip("/")
ELASTIC_API_KEY = os.environ["ELASTIC_API_KEY"]

MODEL = os.getenv("DIGNITY_AGENT_MODEL", "gemini-2.5-flash")

DENIAL_TOOL_NAMES = """
Available tools for this specialist. Use these exact names only:
- list_case_documents
- search_case_documents
- dignity_search_ssa_policy

Never abbreviate, pluralize, rename, or partially type a tool name. The SSA
policy search tool is exactly dignity_search_ssa_policy.
"""

ORCHESTRATOR_TOOL_NAMES = """
Available tools for this orchestrator. Use these exact names only:
- list_case_documents
- search_case_documents
- dignity_search_ssa_policy
- dignity_search_ssa_forms
- dignity_get_advocate_contact
- dignity_search_case_memory

Never abbreviate, pluralize, rename, or partially type a tool name. The SSA
policy search tool is exactly dignity_search_ssa_policy.
"""

_MCP_PARAMS = StreamableHTTPConnectionParams(
    url=f"{KIBANA_URL}/api/agent_builder/mcp",
    headers={
        "Authorization": f"ApiKey {ELASTIC_API_KEY}",
        "kbn-xsrf": "true",
    },
    timeout=30,
    sse_read_timeout=300,
)


def _mcp_tools(tool_filter: list[str]) -> MCPToolset:
    return MCPToolset(connection_params=_MCP_PARAMS, tool_filter=tool_filter)


def build_agents(
    list_case_documents: Callable[..., dict[str, Any]],
    search_case_documents: Callable[..., dict[str, Any]],
) -> tuple[Agent, Agent]:
    scoped_case_tools = [
        FunctionTool(list_case_documents),
        FunctionTool(search_case_documents),
    ]

    denial_policy_tools = _mcp_tools(["dignity_search_ssa_policy"])
    orchestrator_mcp_tools = _mcp_tools(
        [
            "dignity_search_ssa_policy",
            "dignity_search_ssa_forms",
            "dignity_search_case_memory",
            "dignity_get_advocate_contact",
        ]
    )

    denial_analyst = Agent(
        name="denial_analyst",
        model=MODEL,
        description=(
            "Specialist agent for reading and analyzing SSA disability denial notices. "
            "Extracts denial reasons, cited policy, and evidence problems. "
            "Does not draft letters, records requests, or advocate packets."
        ),
        instruction="""
You are a denial analysis specialist for the selected disability denial case.

Your job is precise and focused:
{exact_tool_names}

1. Use list_case_documents to see what documents exist in the selected case.
2. Use search_case_documents to retrieve the denial notice and understand the denial reason.
3. Use dignity_search_ssa_policy to find SSA/POMS rules for the denial issues,
   medically determinable impairment, symptom evaluation, RFC, and medical opinions,
   only when those rules directly explain or contradict the denial reason.

Use only the case documents available through the scoped case tools. If doctor
records are not present, say they are missing.

Only report medical evidence from retrieved documents whose document_type is
medical_record or medication_list. Do not treat a denial_letter PDF as a doctor
record. Do not invent provider names, exam findings, or doctor statements.

Do NOT draft letters, records requests, advocate alerts, or full advocate packets.
That is the orchestrator's job.

When reporting:
- State the denial reason clearly.
- Quote or closely paraphrase retrieved denial text.
- Cite retrieved policy doc IDs and HTTPS secure.ssa.gov policy URLs.
- Say "possible missing evidence" when the denial implies a gap but does not explicitly state one.
- Separate facts found in selected case documents from policy requirements.
- Recommend human review before any action is taken.
""".format(exact_tool_names=DENIAL_TOOL_NAMES),
        tools=[*scoped_case_tools, denial_policy_tools],
    )

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
SSA policy and selected case evidence from Elastic, identify possible missing evidence,
and prepare an advocate-ready review packet.

Analyze the selected disability denial case.

{exact_tool_names}

Required workflow:
1. Use list_case_documents to inspect the selected case packet.
2. Use search_case_documents to retrieve the denial reason and any uploaded case evidence.
3. Use dignity_search_ssa_policy to retrieve relevant SSA/POMS policy for the denial issue,
   medically determinable impairment, symptom evaluation, RFC, sustained work,
   medical opinions, and vocational rules.
4. Use dignity_search_ssa_forms for reconsideration, SSA-561, SSA-827, SSA-1696,
   HA-501, good cause, and representation workflow questions.
5. Use dignity_get_advocate_contact before drafting any advocate alert. If no advocate
   contact is present for the selected case, say so and leave the alert draft empty.
6. Use dignity_search_case_memory if asked about prior saved findings, packets,
   action logs, or advocate memory.

Use only the case documents available through the scoped case tools. If doctor
records are not present, say they are missing.

Only report medical evidence from retrieved documents whose document_type is
medical_record or medication_list. Do not treat a denial_letter PDF as a doctor
record. Do not invent provider names, exam findings, or doctor statements.

When answering:
- Cite retrieved document IDs and policy URLs when available.
- Separate facts found in selected case documents from policy requirements.
- Say "possible missing evidence" when uncertainty remains.
- Recommend human review before sending any external message.
- Keep the output judge-readable: denial reason, retrieved evidence, missing proof,
  recommended actions, and packet-ready summary.
- Prefer HTTPS secure.ssa.gov URLs in citations.
""".format(exact_tool_names=ORCHESTRATOR_TOOL_NAMES),
        tools=[*scoped_case_tools, orchestrator_mcp_tools],
    )

    return root_agent, denial_analyst
