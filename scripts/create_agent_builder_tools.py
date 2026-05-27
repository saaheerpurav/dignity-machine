from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOLS_PATH = ROOT / "config" / "elastic_agent_tools.json"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ.setdefault(name, value)


class KibanaClient:
    def __init__(self, base_url: str, api_key: str, space: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.prefix = f"/s/{space}/api/agent_builder" if space else "/api/agent_builder"

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
            "kbn-xsrf": "true",
        }
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=60) as response:
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Kibana {method} {path} failed: HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Kibana {method} {path} failed: {exc}") from exc

    def list_tools(self) -> Any:
        return self.request("GET", f"{self.prefix}/tools")

    def get_tool(self, tool_id: str) -> Any | None:
        try:
            return self.request("GET", f"{self.prefix}/tools/{tool_id}")
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise

    def create_tool(self, tool: dict[str, Any]) -> Any:
        return self.request("POST", f"{self.prefix}/tools", tool)

    def update_tool(self, tool: dict[str, Any]) -> Any:
        tool_id = tool["id"]
        payload = {key: value for key, value in tool.items() if key != "id"}
        return self.request("PUT", f"{self.prefix}/tools/{tool_id}", payload)

    def execute_tool(self, tool_id: str, params: dict[str, Any]) -> Any:
        return self.request(
            "POST",
            f"{self.prefix}/tools/_execute",
            {"tool_id": tool_id, "tool_params": params},
        )


def load_tools(path: Path) -> list[dict[str, Any]]:
    tools = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tools, list):
        raise ValueError("Tool manifest must be a JSON array.")
    for tool in tools:
        for field in ("id", "type", "description", "configuration"):
            if field not in tool:
                raise ValueError(f"Tool is missing required field {field}: {tool}")
        if tool["id"].startswith(("search.", "platform.", "security.", "observability.")):
            raise ValueError(f"Tool ID uses a protected or risky namespace: {tool['id']}")
    return tools


def run(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    tools = load_tools(args.tools_path)
    print(f"loaded {len(tools)} tool definitions")
    if args.dry_run:
        for tool in tools:
            print(f"dry-run {tool['id']} ({tool['type']})")
        return 0

    kibana_url = args.kibana_url or os.getenv("KIBANA_URL")
    api_key = args.api_key or os.getenv("KIBANA_API_KEY") or os.getenv("ELASTIC_API_KEY")
    if not kibana_url:
        raise RuntimeError("Set KIBANA_URL in .env or pass --kibana-url. ELASTIC_URL is not enough for Agent Builder tools.")
    if not api_key:
        raise RuntimeError("Set KIBANA_API_KEY or ELASTIC_API_KEY in .env.")

    client = KibanaClient(kibana_url, api_key, space=args.space)
    for tool in tools:
        tool_id = tool["id"]
        existing = client.get_tool(tool_id)
        if existing:
            print(f"updating {tool_id} ...")
            client.update_tool(tool)
        else:
            print(f"creating {tool_id} ...")
            client.create_tool(tool)

    if args.test:
        tests = {
            "dignity.search_ssa_policy": {"nlQuery": "fibromyalgia severity functional limitations RFC"},
            "dignity.search_ssa_forms": {"nlQuery": "SSA-561 reconsideration deadline good cause late appeal"},
            "dignity.search_case_documents": {"nlQuery": "Maria missing rheumatology records functional capacity statement"},
            "dignity.search_case_memory": {"nlQuery": "case_maria_lopez_fibro_001 packet gaps advocate"},
            "dignity.get_maria_documents": {"case_id": "case_maria_lopez_fibro_001", "limit": 5},
            "dignity.get_advocate_contact": {"case_id": "case_maria_lopez_fibro_001", "limit": 5},
        }
        for tool_id, params in tests.items():
            print(f"testing {tool_id} ...")
            result = client.execute_tool(tool_id, params)
            print(json.dumps(result, indent=2)[:1600])

    print("tool upload complete")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update Elastic Agent Builder tools for Dignity Machine.")
    parser.add_argument("--tools-path", type=Path, default=DEFAULT_TOOLS_PATH)
    parser.add_argument("--kibana-url", help="Kibana base URL. Defaults to KIBANA_URL from .env.")
    parser.add_argument("--api-key", help="Kibana/Elasticsearch API key. Defaults to KIBANA_API_KEY or ELASTIC_API_KEY from .env.")
    parser.add_argument("--space", help="Kibana space ID, if not using the default space.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print tool IDs without calling Kibana.")
    parser.add_argument("--test", action="store_true", help="Execute basic smoke tests after upload.")
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
