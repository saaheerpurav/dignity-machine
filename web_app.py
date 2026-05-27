from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parent
DEFAULT_QUERY = (
    "Analyze Maria Lopez's denial. Use Elastic tools to find the denial reason, "
    "relevant SSA policy, missing evidence, and what should go into the advocate packet."
)


class AnalyzeRequest(BaseModel):
    query: str = DEFAULT_QUERY


app = FastAPI(title="Dignity Machine Test UI")


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, value = line.split("=", 1)
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        values[key.strip()] = value
    return values


def agent_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(load_dotenv(ROOT / ".env"))
    env.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    env.setdefault("GOOGLE_CLOUD_PROJECT", "integral-tensor-497618-a8")
    env.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
    return env


def extract_agent_answer(output: str) -> str:
    match = re.search(r"\[dignity_machine\]:\s*(.*?)(?:\n[A-Z]:\\|\Z)", output, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return output.strip()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dignity Machine Test UI</title>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      background: #f4f6f8;
      color: #17202a;
    }}
    body {{
      margin: 0;
      padding: 24px;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
    }}
    header {{
      margin-bottom: 18px;
    }}
    h1 {{
      font-size: 28px;
      margin: 0 0 8px;
      letter-spacing: 0;
    }}
    p {{
      margin: 0;
      color: #4b5563;
      line-height: 1.45;
    }}
    section {{
      background: #ffffff;
      border: 1px solid #d7dde4;
      border-radius: 8px;
      padding: 16px;
      margin: 14px 0;
    }}
    label {{
      display: block;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    textarea {{
      width: 100%;
      min-height: 120px;
      box-sizing: border-box;
      resize: vertical;
      padding: 12px;
      border: 1px solid #b8c0cc;
      border-radius: 6px;
      font: 14px/1.45 Consolas, Monaco, monospace;
    }}
    button {{
      margin-top: 12px;
      border: 0;
      border-radius: 6px;
      padding: 10px 14px;
      background: #0f766e;
      color: #ffffff;
      font-weight: 700;
      cursor: pointer;
    }}
    button:disabled {{
      opacity: 0.6;
      cursor: wait;
    }}
    pre {{
      min-height: 260px;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font: 14px/1.5 Consolas, Monaco, monospace;
    }}
    #answer {{
      min-height: 160px;
      line-height: 1.5;
    }}
    #answer h1, #answer h2, #answer h3 {{
      margin: 16px 0 8px;
      letter-spacing: 0;
    }}
    #answer h1 {{
      font-size: 24px;
    }}
    #answer h2 {{
      font-size: 20px;
    }}
    #answer h3 {{
      font-size: 17px;
    }}
    #answer p {{
      margin: 8px 0;
      color: #17202a;
    }}
    #answer ul, #answer ol {{
      padding-left: 24px;
    }}
    #answer code {{
      background: #eef2f7;
      border-radius: 4px;
      padding: 2px 4px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 8px;
      margin-top: 12px;
    }}
    .pill {{
      border: 1px solid #d7dde4;
      border-radius: 6px;
      padding: 8px;
      background: #f8fafc;
      font-size: 13px;
      color: #334155;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Dignity Machine Test UI</h1>
      <p>Minimal local harness for the ADK Gemini agent connected to Elastic MCP.</p>
      <div class="meta">
        <div class="pill">Case: Maria Lopez</div>
        <div class="pill">Project: integral-tensor-497618-a8</div>
        <div class="pill">Tools: Elastic Agent Builder MCP</div>
      </div>
    </header>
    <section>
      <label for="query">Agent query</label>
      <textarea id="query">{html.escape(DEFAULT_QUERY)}</textarea>
      <button id="run">Run analysis</button>
    </section>
    <section>
      <label>Output</label>
      <div id="answer">Ready.</div>
    </section>
  </main>
  <script>
    const run = document.getElementById('run');
    const query = document.getElementById('query');
    const answer = document.getElementById('answer');

    marked.setOptions({{ breaks: true, gfm: true }});

    run.addEventListener('click', async () => {{
      run.disabled = true;
      answer.textContent = 'Running ADK agent. This can take 30-90 seconds...';
      try {{
        const response = await fetch('/api/analyze', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ query: query.value }})
        }});
        const data = await response.json();
        if (!response.ok) {{
          throw new Error(data.detail || 'Request failed');
        }}
        answer.innerHTML = marked.parse(data.answer || '');
      }} catch (error) {{
        answer.textContent = 'Error: ' + error.message;
      }} finally {{
        run.disabled = false;
      }}
    }});
  </script>
</body>
</html>"""


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict[str, str | int]:
    query = payload.query.strip() or DEFAULT_QUERY
    command = [
        "adk",
        "run",
        "dignity_agent",
        query,
        "--in_memory",
        "--timeout",
        "180s",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=agent_env(),
            text=True,
            capture_output=True,
            timeout=210,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail=f"ADK run timed out: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "ADK run failed."
        raise HTTPException(status_code=500, detail=detail)

    answer = extract_agent_answer(completed.stdout)
    return {
        "answer": answer,
        "returncode": completed.returncode,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web_app:app", host="127.0.0.1", port=3000, reload=False)
