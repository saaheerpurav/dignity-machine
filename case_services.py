from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
PDF_UPLOAD_DIR = ROOT / "static" / "documents" / "uploads"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SCANNED_PDF_MESSAGE = "No readable text found. Upload a text-based PDF for this demo."
IRRELEVANT_PDF_MESSAGE = "This PDF does not look like a disability denial letter. Try the example denial or upload a notice from Social Security."
EXAMPLE_CASE_ID = "case_6f3a2c91b7d4"
EXAMPLE_DOC_ID = "denial_pdf_seed_001"


class CaseError(Exception):
    pass


class PdfValidationError(CaseError):
    pass


class PdfTextExtractionError(CaseError):
    pass


class PdfRelevanceError(CaseError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def preview_text(value: str, limit: int = 900) -> str:
    normalized = re.sub(r"\s+", " ", value).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "..."


def available_pdf_url(case_id: str, pdf_url: str | None) -> str | None:
    if not pdf_url:
        return None
    if pdf_url == "/documents/example-denial.pdf":
        return pdf_url
    prefix = "/documents/uploads/"
    if pdf_url.startswith(prefix):
        path = ROOT / "static" / "documents" / "uploads" / Path(pdf_url.removeprefix(prefix)).name
        return pdf_url if path.exists() else None
    return pdf_url


class PdfTextExtractor:
    def extract(self, data: bytes) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise PdfTextExtractionError("pypdf is not installed. Install requirements.txt and retry.") from exc

        try:
            reader = PdfReader(BytesIO(data))
            pages = [(page.extract_text() or "").strip() for page in reader.pages]
        except Exception as exc:
            raise PdfValidationError("Could not read this PDF. Upload a valid text-based PDF.") from exc

        text = "\n\n".join(page for page in pages if page)
        if len(re.sub(r"\s+", "", text)) < 40:
            raise PdfTextExtractionError(SCANNED_PDF_MESSAGE)
        return text


class PdfRelevanceClassifier:
    strong_signals = {
        "social security": 3,
        "ssa": 3,
        "supplemental security income": 3,
        "disability": 2,
        "not disabled": 4,
        "denied": 3,
        "denial": 3,
        "medical evidence": 2,
        "work activity": 2,
        "appeal": 2,
        "reconsideration": 2,
        "determination": 2,
        "notice date": 2,
        "60 days": 2,
    }
    irrelevant_signals = {
        "resume",
        "curriculum vitae",
        "invoice",
        "amount due",
        "subtotal",
        "purchase order",
        "quarterly report",
        "annual report",
        "abstract",
        "references",
    }

    def classify(self, text: str) -> dict[str, Any]:
        normalized = re.sub(r"\s+", " ", text.lower()).strip()
        matched = [signal for signal in self.strong_signals if signal in normalized]
        if "notice date" not in matched and re.search(
            r"\b(?:notice\s+)?date:\s*(?:[A-Z][a-z]+ \d{1,2}, \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            text,
            flags=re.IGNORECASE,
        ):
            matched.append("notice date")
        missing = [signal for signal in self.strong_signals if signal not in matched]
        irrelevant = [signal for signal in self.irrelevant_signals if signal in normalized]
        score = sum(self.strong_signals[signal] for signal in matched)
        has_ssa_context = any(signal in matched for signal in ("social security", "ssa", "supplemental security income"))
        has_disability_context = "disability" in matched or "not disabled" in matched
        has_denial_context = any(signal in matched for signal in ("denied", "denial", "not disabled", "determination"))
        has_appeal_context = any(signal in matched for signal in ("appeal", "reconsideration", "60 days"))
        has_notice_date = "notice date" in matched

        if has_ssa_context and has_disability_context and has_denial_context and has_notice_date and score >= 10:
            kind = "valid_denial"
            message = "Readable Social Security disability denial PDF."
        elif has_ssa_context and has_disability_context and has_denial_context and score >= 10:
            kind = "possible_denial"
            message = "Readable PDF, but no notice date found."
        elif has_disability_context and has_denial_context and score >= 6:
            kind = "possible_denial"
            message = "Readable PDF appears to be an incomplete disability denial."
        elif has_ssa_context and has_disability_context and has_appeal_context and score >= 7:
            kind = "possible_denial"
            message = "Readable PDF appears related to a Social Security disability appeal."
        else:
            kind = "irrelevant"
            message = IRRELEVANT_PDF_MESSAGE

        if irrelevant and score < 10:
            kind = "irrelevant"
            message = IRRELEVANT_PDF_MESSAGE

        confidence = min(0.98, max(0.05, score / 18))
        if kind == "irrelevant":
            confidence = max(0.75, 1 - confidence)
        elif kind == "possible_denial":
            confidence = min(confidence, 0.72)

        return {
            "type": kind,
            "confidence": round(confidence, 2),
            "matched_signals": matched,
            "missing_signals": missing,
            "message": message,
        }


class ElasticCaseStore:
    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        api_key = os.getenv("ELASTIC_API_KEY")
        if not api_key:
            raise RuntimeError("ELASTIC_API_KEY is missing.")
        return {"Authorization": f"ApiKey {api_key}", "Content-Type": content_type}

    def _url(self) -> str:
        value = os.getenv("ELASTIC_URL", "").rstrip("/")
        if not value:
            raise RuntimeError("ELASTIC_URL is missing.")
        return value

    def request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(f"{self._url()}{path}", data=body, headers=self._headers(), method=method)
        try:
            with urlopen(request, timeout=60) as response:
                raw = response.read()
                return {} if not raw else json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Elastic {method} {path} failed: HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Elastic {method} {path} failed: {exc}") from exc

    def bulk(self, records_by_index: dict[str, list[dict[str, Any]]]) -> None:
        if not records_by_index:
            return
        lines: list[str] = []
        for index_name, records in records_by_index.items():
            for record in records:
                document_id = (
                    record.get("gap_id")
                    or record.get("packet_id")
                    or record.get("event_id")
                    or record.get("doc_id")
                    or stable_id("doc")
                )
                lines.append(json.dumps({"index": {"_index": index_name, "_id": document_id}}, separators=(",", ":")))
                lines.append(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
        body = ("\n".join(lines) + "\n").encode("utf-8")
        request = Request(
            f"{self._url()}/_bulk?refresh=true",
            data=body,
            headers=self._headers("application/x-ndjson"),
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Elastic bulk write failed: HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Elastic bulk write failed: {exc}") from exc
        if result.get("errors"):
            failures = [
                item["index"].get("error")
                for item in result.get("items", [])
                if item.get("index", {}).get("error")
            ]
            raise RuntimeError(f"Elastic bulk write had errors: {failures[:3]}")

    def index_case_document(self, document: dict[str, Any]) -> None:
        self.bulk({"case_documents": [document]})

    def case_document_count(self, case_id: str) -> int:
        result = self.request_json(
            "POST",
            "/case_documents/_count",
            {"query": {"term": {"case_id": case_id}}},
        )
        return int(result.get("count", 0))

    def list_documents(self, case_id: str, limit: int = 20) -> dict[str, Any]:
        limit = max(1, min(int(limit or 20), 50))
        result = self.request_json(
            "POST",
            "/case_documents/_search",
            {
                "query": {"bool": {"filter": [{"term": {"case_id": case_id}}]}},
                "sort": [{"created_at": {"order": "asc"}}],
                "size": limit,
            },
        )
        documents = []
        for hit in result.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            documents.append(
                {
                    "case_id": source.get("case_id"),
                    "doc_id": source.get("doc_id"),
                    "document_type": source.get("document_type"),
                    "source_name": source.get("source_name"),
                    "title": source.get("title"),
                    "created_at": source.get("created_at"),
                    "pdf_url": source.get("pdf_url") or (source.get("extracted_fields") or {}).get("pdf_url"),
                    "document_classification": source.get("document_classification"),
                    "content_preview": preview_text(str(source.get("content", "")), 500),
                }
            )
        return {"case_id": case_id, "documents": documents, "document_count": len(documents)}

    def search_documents(self, case_id: str, query: str, limit: int = 6) -> dict[str, Any]:
        limit = max(1, min(int(limit or 6), 20))
        text_query = (query or "").strip()
        must_clause: dict[str, Any] = {"match_all": {}}
        if text_query:
            must_clause = {
                "multi_match": {
                    "query": text_query,
                    "fields": [
                        "title^2",
                        "content^4",
                        "embedding_text^3",
                        "source_name",
                        "document_type",
                        "condition_tags",
                        "appeal_stage_tags",
                    ],
                }
            }
        result = self.request_json(
            "POST",
            "/case_documents/_search",
            {
                "query": {
                    "bool": {
                        "must": [must_clause],
                        "filter": [{"term": {"case_id": case_id}}],
                    }
                },
                "highlight": {"fields": {"content": {"fragment_size": 260, "number_of_fragments": 2}}},
                "size": limit,
            },
        )
        documents = []
        for hit in result.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            highlights = hit.get("highlight", {}).get("content", [])
            excerpt = " ".join(re.sub(r"</?em>", "", item) for item in highlights)
            if not excerpt:
                excerpt = preview_text(str(source.get("content", "")), 600)
            documents.append(
                {
                    "case_id": source.get("case_id"),
                    "doc_id": source.get("doc_id"),
                    "document_type": source.get("document_type"),
                    "source_name": source.get("source_name"),
                    "title": source.get("title"),
                    "created_at": source.get("created_at"),
                    "excerpt": excerpt,
                }
            )
        return {"case_id": case_id, "query": text_query, "documents": documents}

    def case_text(self, case_id: str, limit: int = 50) -> str:
        limit = max(1, min(int(limit or 50), 100))
        result = self.request_json(
            "POST",
            "/case_documents/_search",
            {
                "query": {"bool": {"filter": [{"term": {"case_id": case_id}}]}},
                "_source": ["title", "source_name", "document_type", "content", "embedding_text"],
                "size": limit,
            },
        )
        chunks: list[str] = []
        for hit in result.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            chunks.extend(
                str(source.get(field, ""))
                for field in ("title", "source_name", "document_type", "content", "embedding_text")
                if source.get(field)
            )
        return "\n".join(chunks)


class CaseService:
    def __init__(self, store: ElasticCaseStore, extractor: PdfTextExtractor) -> None:
        self.store = store
        self.extractor = extractor
        self.classifier = PdfRelevanceClassifier()

    def validate_pdf_upload(self, filename: str, content_type: str | None, data: bytes) -> None:
        if not filename.lower().endswith(".pdf"):
            raise PdfValidationError("Upload one PDF file.")
        if content_type and content_type not in {"application/pdf", "application/octet-stream"}:
            raise PdfValidationError("Upload one PDF file.")
        if not data:
            raise PdfValidationError("Upload one PDF file.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise PdfValidationError("PDF is too large. Upload a file under 10 MB.")

    def create_from_pdf(self, filename: str, content_type: str | None, data: bytes) -> dict[str, Any]:
        self.validate_pdf_upload(filename, content_type, data)
        text = self.extractor.extract(data)
        classification = self.classifier.classify(text)
        if classification["type"] == "irrelevant":
            raise PdfRelevanceError(IRRELEVANT_PDF_MESSAGE)
        case_id = stable_id("case")
        doc_id = stable_id("denial_pdf")
        pdf_url = self._save_uploaded_pdf(case_id, data)
        return self._index_pdf_text(
            case_id,
            doc_id,
            filename,
            text,
            Path(filename).name or "Uploaded denial PDF",
            pdf_url=pdf_url,
            classification=classification,
        )

    def ensure_example_case(self) -> dict[str, Any]:
        pdf_path = ROOT / "static" / "documents" / "example-denial.pdf"
        if not pdf_path.exists():
            pdf_path = ROOT / "frontend" / "public" / "documents" / "example-denial.pdf"
        data = pdf_path.read_bytes()
        text = self.extractor.extract(data)
        self._index_pdf_text(
            EXAMPLE_CASE_ID,
            EXAMPLE_DOC_ID,
            pdf_path.name,
            text,
            "Social Security disability denial notice",
            classification=self.classifier.classify(text),
        )
        return self.summary(EXAMPLE_CASE_ID)

    def summary(self, case_id: str) -> dict[str, Any]:
        result = self.store.list_documents(case_id, limit=1)
        docs = result["documents"]
        if not docs:
            raise CaseError(f"Case not found: {case_id}")
        first = docs[0]
        classification = first.get("document_classification")
        if not isinstance(classification, dict):
            classification = self.classifier.classify(self.store.case_text(case_id))
        pdf_url = first.get("pdf_url") or ("/documents/example-denial.pdf" if case_id == EXAMPLE_CASE_ID else None)
        return {
            "case_id": case_id,
            "title": first.get("title") or "Selected denial case",
            "source_name": first.get("source_name") or "Uploaded PDF",
            "extracted_text_preview": first.get("content_preview") or "",
            "document_count": self.store.case_document_count(case_id),
            "pdf_url": available_pdf_url(case_id, pdf_url),
            "document_classification": classification,
        }

    def _save_uploaded_pdf(self, case_id: str, data: bytes) -> str:
        PDF_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        path = PDF_UPLOAD_DIR / f"{case_id}.pdf"
        path.write_bytes(data)
        return f"/documents/uploads/{case_id}.pdf"

    def _index_pdf_text(
        self,
        case_id: str,
        doc_id: str,
        filename: str,
        text: str,
        source_name: str,
        pdf_url: str | None = None,
        classification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_name = Path(filename).name or "denial.pdf"
        title = Path(safe_name).stem.replace("-", " ").replace("_", " ").strip().title() or "Denial PDF"
        document = {
            "case_id": case_id,
            "doc_id": doc_id,
            "document_type": "denial_letter",
            "source_name": source_name,
            "created_at": now_iso(),
            "title": title,
            "content": text,
            "extracted_fields": {"source_filename": safe_name, "pdf_url": pdf_url},
            "pdf_url": pdf_url,
            "document_classification": classification or self.classifier.classify(text),
            "condition_tags": [],
            "appeal_stage_tags": [],
            "embedding_text": f"{title}\n{source_name}\n{text}",
        }
        self.store.index_case_document(document)
        resolved_pdf_url = pdf_url or ("/documents/example-denial.pdf" if case_id == EXAMPLE_CASE_ID else None)
        return {
            "case_id": case_id,
            "title": title,
            "source_name": source_name,
            "extracted_text_preview": preview_text(text),
            "document_count": self.store.case_document_count(case_id),
            "pdf_url": resolved_pdf_url,
            "document_classification": document["document_classification"],
        }
