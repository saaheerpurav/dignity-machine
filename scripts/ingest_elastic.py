from __future__ import annotations

import argparse
import base64
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

DATASETS = {
    "ssa_policy": ROOT / "data" / "processed" / "ssa_policy.jsonl",
    "ssa_forms": ROOT / "data" / "processed" / "ssa_forms.jsonl",
}

INDEX_MAPPINGS: dict[str, dict[str, Any]] = {
    "ssa_policy": {
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "section": {"type": "text"},
                "url": {"type": "keyword"},
                "retrieved_at": {"type": "date"},
                "content": {"type": "text"},
                "chunk_index": {"type": "integer"},
                "condition_tags": {"type": "keyword"},
                "appeal_stage_tags": {"type": "keyword"},
                "embedding_text": {"type": "text"},
                "content_sha1": {"type": "keyword"},
            }
        }
    },
    "ssa_forms": {
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "source_type": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "section": {"type": "text"},
                "url": {"type": "keyword"},
                "retrieved_at": {"type": "date"},
                "content": {"type": "text"},
                "chunk_index": {"type": "integer"},
                "condition_tags": {"type": "keyword"},
                "appeal_stage_tags": {"type": "keyword"},
                "embedding_text": {"type": "text"},
                "content_sha1": {"type": "keyword"},
            }
        }
    },
    "case_documents": {
        "mappings": {
            "properties": {
                "case_id": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                "document_type": {"type": "keyword"},
                "source_name": {"type": "keyword"},
                "created_at": {"type": "date"},
                "claimant_name": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "content": {"type": "text"},
                "extracted_fields": {"type": "object", "enabled": True},
                "document_classification": {"type": "object", "enabled": True},
                "condition_tags": {"type": "keyword"},
                "appeal_stage_tags": {"type": "keyword"},
                "embedding_text": {"type": "text"},
            }
        }
    },
    "advocate_contacts": {
        "mappings": {
            "properties": {
                "case_id": {"type": "keyword"},
                "contact_id": {"type": "keyword"},
                "name": {"type": "keyword"},
                "relationship": {"type": "keyword"},
                "channel": {"type": "keyword"},
                "destination": {"type": "keyword"},
                "allowed_actions": {"type": "keyword"},
                "created_at": {"type": "date"},
                "content": {"type": "text"},
                "embedding_text": {"type": "text"},
            }
        }
    },
    "evidence_gaps": {
        "mappings": {
            "properties": {
                "gap_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "condition": {"type": "keyword"},
                "gap_type": {"type": "keyword"},
                "description": {"type": "text"},
                "why_it_matters": {"type": "text"},
                "supporting_policy_ids": {"type": "keyword"},
                "supporting_case_doc_ids": {"type": "keyword"},
                "confidence": {"type": "float"},
                "created_at": {"type": "date"},
            }
        }
    },
    "case_tasks": {
        "mappings": {
            "properties": {
                "task_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "mission_id": {"type": "keyword"},
                "task_type": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "description": {"type": "text"},
                "reason": {"type": "text"},
                "status": {"type": "keyword"},
                "source": {"type": "keyword"},
                "created_at": {"type": "date"},
            }
        }
    },
    "deadline_tasks": {
        "mappings": {
            "properties": {
                "deadline_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "mission_id": {"type": "keyword"},
                "notice_date": {"type": "date"},
                "assumed_receipt_date": {"type": "date"},
                "appeal_deadline": {"type": "date"},
                "confidence": {"type": "float"},
                "source": {"type": "keyword"},
                "human_review_required": {"type": "boolean"},
                "created_at": {"type": "date"},
            }
        }
    },
    "review_summaries": {
        "mappings": {
            "properties": {
                "summary_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "mission_id": {"type": "keyword"},
                "status": {"type": "keyword"},
                "denial_summary": {"type": "text"},
                "policy_citations": {"type": "object", "enabled": True},
                "missing_evidence": {"type": "object", "enabled": True},
                "deadline": {"type": "object", "enabled": True},
                "case_task_ids": {"type": "keyword"},
                "records_request_text": {"type": "text"},
                "review_summary": {"type": "text"},
                "next_actions": {"type": "text"},
                "created_at": {"type": "date"},
            }
        }
    },
    "records_requests": {
        "mappings": {
            "properties": {
                "request_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "mission_id": {"type": "keyword"},
                "status": {"type": "keyword"},
                "request_context": {"type": "text"},
                "records_needed": {"type": "text"},
                "placeholder_fields": {"type": "keyword"},
                "records_request_text": {"type": "text"},
                "human_review_note": {"type": "text"},
                "created_at": {"type": "date"},
            }
        }
    },
    "case_facts": {
        "mappings": {
            "properties": {
                "fact_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "field": {"type": "keyword"},
                "label": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "value": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "source": {"type": "keyword"},
                "confidence": {"type": "float"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
            }
        }
    },
    "case_task_updates": {
        "mappings": {
            "properties": {
                "update_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "task_id": {"type": "keyword"},
                "task_type": {"type": "keyword"},
                "from_status": {"type": "keyword"},
                "to_status": {"type": "keyword"},
                "note": {"type": "text"},
                "created_at": {"type": "date"},
            }
        }
    },
    "case_actions": {
        "mappings": {
            "properties": {
                "action_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "action_type": {"type": "keyword"},
                "payload": {"type": "object", "enabled": True},
                "created_at": {"type": "date"},
            }
        }
    },
    "appeal_packets": {
        "mappings": {
            "properties": {
                "packet_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "status": {"type": "keyword"},
                "denial_summary": {"type": "text"},
                "policy_citations": {"type": "object", "enabled": True},
                "medical_evidence_ids": {"type": "keyword"},
                "evidence_gap_ids": {"type": "keyword"},
                "records_request_text": {"type": "text"},
                "advocate_summary": {"type": "text"},
                "deadline_ids": {"type": "keyword"},
                "created_at": {"type": "date"},
            }
        }
    },
    "action_logs": {
        "mappings": {
            "properties": {
                "event_id": {"type": "keyword"},
                "case_id": {"type": "keyword"},
                "event_type": {"type": "keyword"},
                "tool_name": {"type": "keyword"},
                "index_name": {"type": "keyword"},
                "input": {"type": "object", "enabled": True},
                "output": {"type": "object", "enabled": True},
                "created_at": {"type": "date"},
            }
        }
    },
}


class ElasticClient:
    def __init__(self, base_url: str, api_key: str | None, username: str | None, password: str | None, verify_tls: bool) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.username = username
        self.password = password
        self.context = None if verify_tls else ssl._create_unverified_context()

    def request(self, method: str, path: str, body: bytes | None = None, content_type: str = "application/json") -> Any:
        headers = {"Content-Type": content_type}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        elif self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {token}"
        else:
            raise RuntimeError("Set ELASTIC_API_KEY or ELASTIC_USERNAME/ELASTIC_PASSWORD.")

        request = Request(f"{self.base_url}{path}", data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=60, context=self.context) as response:
                raw = response.read()
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Elastic {method} {path} failed: HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Elastic {method} {path} failed: {exc}") from exc

    def put_index(self, index_name: str, mapping: dict[str, Any], recreate: bool) -> None:
        exists = self.index_exists(index_name)
        if exists and recreate:
            self.request("DELETE", f"/{index_name}")
            exists = False
        if not exists:
            self.request("PUT", f"/{index_name}", json.dumps(mapping).encode("utf-8"))

    def index_exists(self, index_name: str) -> bool:
        request = Request(f"{self.base_url}/{index_name}", method="HEAD")
        if self.api_key:
            request.add_header("Authorization", f"ApiKey {self.api_key}")
        elif self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
            request.add_header("Authorization", f"Basic {token}")
        else:
            raise RuntimeError("Set ELASTIC_API_KEY or ELASTIC_USERNAME/ELASTIC_PASSWORD.")
        try:
            with urlopen(request, timeout=30, context=self.context):
                return True
        except HTTPError as exc:
            if exc.code == 404:
                return False
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Elastic HEAD /{index_name} failed: HTTP {exc.code}: {detail}") from exc

    def bulk_index(self, index_name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        lines: list[str] = []
        for record in records:
            document_id = document_id_for(index_name, record)
            lines.append(json.dumps({"index": {"_index": index_name, "_id": document_id}}, separators=(",", ":")))
            lines.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        body = ("\n".join(lines) + "\n").encode("utf-8")
        result = self.request("POST", "/_bulk", body=body, content_type="application/x-ndjson")
        if result.get("errors"):
            failures = [
                item["index"].get("error")
                for item in result.get("items", [])
                if item.get("index", {}).get("error")
            ]
            raise RuntimeError(f"Bulk ingest to {index_name} had errors: {failures[:3]}")
        return result


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} is not valid JSON: {exc}") from exc
    return records


def document_id_for(index_name: str, record: dict[str, Any]) -> str:
    if index_name in {"ssa_policy", "ssa_forms"}:
        return str(record["chunk_id"])
    if index_name == "case_documents":
        return str(record["doc_id"])
    if index_name == "advocate_contacts":
        return str(record["contact_id"])
    return str(record.get("id") or record.get(f"{index_name[:-1]}_id") or record.get("doc_id"))


def validate_records(index_name: str, records: list[dict[str, Any]]) -> None:
    required = {
        "ssa_policy": ["doc_id", "chunk_id", "content", "embedding_text"],
        "ssa_forms": ["doc_id", "chunk_id", "content", "embedding_text"],
    }[index_name]
    for idx, record in enumerate(records):
        missing = [field for field in required if field not in record]
        if missing:
            raise ValueError(f"{index_name} record {idx} missing fields: {missing}")


def load_datasets(selected: list[str]) -> dict[str, list[dict[str, Any]]]:
    loaded: dict[str, list[dict[str, Any]]] = {}
    for index_name in selected:
        path = DATASETS[index_name]
        if not path.exists():
            raise FileNotFoundError(path)
        records = read_jsonl(path)
        validate_records(index_name, records)
        loaded[index_name] = records
    return loaded


def run(args: argparse.Namespace) -> int:
    selected = args.indexes or list(DATASETS)
    invalid = [name for name in selected if name not in DATASETS]
    if invalid:
        raise ValueError(f"Unknown dataset indexes: {invalid}")

    loaded = load_datasets(selected)
    print("validated datasets:")
    for index_name, records in loaded.items():
        print(f"  {index_name}: {len(records)} records")

    if args.dry_run:
        print("dry run only; no Elastic writes performed")
        return 0

    base_url = args.url or os.getenv("ELASTIC_URL")
    if not base_url:
        raise RuntimeError("Set ELASTIC_URL or pass --url.")
    client = ElasticClient(
        base_url=base_url,
        api_key=os.getenv("ELASTIC_API_KEY"),
        username=os.getenv("ELASTIC_USERNAME"),
        password=os.getenv("ELASTIC_PASSWORD"),
        verify_tls=not args.insecure_tls,
    )

    for index_name in INDEX_MAPPINGS:
        if index_name in loaded or args.create_empty_indexes:
            print(f"creating index {index_name} ...")
            client.put_index(index_name, INDEX_MAPPINGS[index_name], recreate=args.recreate)

    for index_name, records in loaded.items():
        print(f"bulk indexing {len(records)} records into {index_name} ...")
        client.bulk_index(index_name, records)

    print("ingest complete")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Elastic indexes and ingest Dignity Machine JSONL data.")
    parser.add_argument("--url", help="Elastic base URL. Defaults to ELASTIC_URL.")
    parser.add_argument("--index", dest="indexes", action="append", choices=sorted(DATASETS), help="Dataset index to ingest. Repeatable. Defaults to all datasets.")
    parser.add_argument("--dry-run", action="store_true", help="Validate local JSONL files without writing to Elastic.")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate selected indexes before ingesting.")
    parser.add_argument("--create-empty-indexes", action="store_true", help="Also create empty workflow indexes for action plans and generated artifacts.")
    parser.add_argument("--insecure-tls", action="store_true", help="Disable TLS certificate verification for local/dev clusters.")
    args = parser.parse_args()
    try:
        return run(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
