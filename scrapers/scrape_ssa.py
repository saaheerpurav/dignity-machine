from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


@dataclass(frozen=True)
class Source:
    doc_id: str
    url: str
    source_type: str
    title: str
    index: str
    condition_tags: list[str]
    appeal_stage_tags: list[str]


SOURCES: list[Source] = [
    Source(
        doc_id="poms_di_22505_001_medical_and_nonmedical_evidence",
        url="https://secure.ssa.gov/poms.nsf/lnx/0422505001",
        source_type="POMS Evidence",
        title="POMS DI 22505.001: Medical and Nonmedical Evidence",
        index="ssa_policy",
        condition_tags=["medical_evidence", "nonmedical_evidence"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_22505_003_acceptable_medical_source",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0422505003!opendocument",
        source_type="POMS Evidence",
        title="POMS DI 22505.003: Evidence from an Acceptable Medical Source",
        index="ssa_policy",
        condition_tags=["medical_evidence"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_22505_007_developing_medical_source_evidence",
        url="https://secure.ssa.gov/apps10/poms.nsf/links/0422505007",
        source_type="POMS Evidence",
        title="POMS DI 22505.007: Developing Evidence from Medical Sources",
        index="ssa_policy",
        condition_tags=["medical_evidence", "records_request", "medical_source_statement"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24501_016_evidence_evaluation",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0424501016",
        source_type="POMS Evidence",
        title="POMS DI 24501.016: Evidence Evaluation",
        index="ssa_policy",
        condition_tags=["evidence_evaluation", "supportability", "consistency"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24501_020_medically_determinable_impairment",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424501020",
        source_type="POMS Evidence",
        title="POMS DI 24501.020: Establishing a Medically Determinable Impairment",
        index="ssa_policy",
        condition_tags=["medical_evidence", "medically_determinable_impairment"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24501_021_evaluating_symptoms",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424501021",
        source_type="POMS Symptoms",
        title="POMS DI 24501.021: Evaluating Symptoms",
        index="ssa_policy",
        condition_tags=["symptoms", "pain", "fatigue", "consistency", "functional_limitations"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24503_015_other_medical_evidence",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0424503015",
        source_type="POMS Evidence",
        title="POMS DI 24503.015: Evaluating Other Medical Evidence",
        index="ssa_policy",
        condition_tags=["medical_evidence", "treatment_response", "prognosis"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24503_025_medical_opinions_after_2017",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424503025",
        source_type="POMS Medical Opinion",
        title="POMS DI 24503.025: Evaluating Medical Opinions and Prior Administrative Medical Findings - Claims Filed On or After March 27, 2017",
        index="ssa_policy",
        condition_tags=["medical_opinion", "supportability", "consistency"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24503_030_medical_opinion_articulation_after_2017",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0424503030",
        source_type="POMS Medical Opinion",
        title="POMS DI 24503.030: Articulation Requirements for Medical Opinions and Prior Administrative Medical Findings - Claims Filed On or After March 27, 2017",
        index="ssa_policy",
        condition_tags=["medical_opinion", "supportability", "consistency", "denial_rationale"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24505_030_potential_impairment",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0424505030!opendocument",
        source_type="POMS Evidence",
        title="POMS DI 24505.030: Identifying, Developing Evidence of, and Evaluating a Potential Impairment",
        index="ssa_policy",
        condition_tags=["potential_impairment", "medical_evidence", "unlisted_condition"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_26515_001_adult_initial_rationale",
        url="https://secure.ssa.gov/poms.nsf/lnx/0426515001",
        source_type="POMS Rationale",
        title="POMS DI 26515.001: Documenting the Rationale in Adult Initial Claims",
        index="ssa_policy",
        condition_tags=["denial_rationale", "medical_opinion", "rfc"],
        appeal_stage_tags=["initial", "reconsideration"],
    ),
    Source(
        doc_id="poms_di_24510_000_rfc_toc",
        url="https://secure.ssa.gov/poms.nsf/links/0424510000",
        source_type="POMS RFC",
        title="POMS DI 24510.000: Residual Functional Capacity",
        index="ssa_policy",
        condition_tags=["rfc", "functional_capacity"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24510_006_rfc_assessment",
        url="https://secure.ssa.gov/poms.NSF/lnx/0424510006",
        source_type="POMS RFC",
        title="POMS DI 24510.006: Assessing RFC",
        index="ssa_policy",
        condition_tags=["rfc", "functional_capacity"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24510_057_sustainability_rfc",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424510057",
        source_type="POMS RFC",
        title="POMS DI 24510.057: Sustainability and RFC Assessment",
        index="ssa_policy",
        condition_tags=["rfc", "functional_capacity", "sustained_work"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24515_012_evaluating_lay_evidence",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424515012",
        source_type="POMS Evidence",
        title="POMS DI 24515.012: Evaluating Lay Evidence",
        index="ssa_policy",
        condition_tags=["lay_evidence", "function_report", "daily_activities"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24515_076_fibromyalgia",
        url="https://secure.ssa.gov/poms.NSF/lnx/0424515076",
        source_type="POMS Condition Guidance",
        title="POMS DI 24515.076: Evaluation of Fibromyalgia (SSR 12-2p)",
        index="ssa_policy",
        condition_tags=["fibromyalgia", "chronic_pain", "medically_determinable_impairment"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24515_075_chronic_fatigue_syndrome",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424515075",
        source_type="POMS Condition Guidance",
        title="POMS DI 24515.075: Evaluating Claims Involving Chronic Fatigue Syndrome",
        index="ssa_policy",
        condition_tags=["chronic_fatigue_syndrome", "chronic_symptoms", "medically_determinable_impairment"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24555_001_interstitial_cystitis",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424555001",
        source_type="POMS Condition Guidance",
        title="POMS DI 24555.001: Evaluating Cases Involving Interstitial Cystitis (SSR 15-1p)",
        index="ssa_policy",
        condition_tags=["interstitial_cystitis", "chronic_pain", "chronic_symptoms"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_25005_001_past_relevant_work",
        url="https://secure.ssa.gov/poms.nsf/lnx/0425005001",
        source_type="POMS Vocational",
        title="POMS DI 25005.001: Past Relevant Work",
        index="ssa_policy",
        condition_tags=["vocational", "past_relevant_work"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_25010_001_medical_vocational_profiles",
        url="https://secure.ssa.gov/poms.nsf/lnx/0425010001",
        source_type="POMS Vocational",
        title="POMS DI 25010.001: Medical-Vocational Profiles",
        index="ssa_policy",
        condition_tags=["vocational", "medical_vocational"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_25025_001_medical_vocational_guidelines",
        url="https://secure.ssa.gov/poms.nsf/lnx/0425025001",
        source_type="POMS Vocational",
        title="POMS DI 25025.001: Medical-Vocational Guidelines",
        index="ssa_policy",
        condition_tags=["vocational", "grid_rules", "medical_vocational"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_gn_03101_020_good_cause_late_appeal",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203101020",
        source_type="POMS Appeals",
        title="POMS GN 03101.020: Good Cause for Extending the Time Limit to File an Appeal",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_gn_03101_040_appeal_initial_determination",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203101040",
        source_type="POMS Appeals",
        title="POMS GN 03101.040: Appeal of an Initial Determination",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["reconsideration"],
    ),
    Source(
        doc_id="poms_gn_03102_100_reconsideration_process",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203102100",
        source_type="POMS Appeals",
        title="POMS GN 03102.100: Reconsideration Process",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["reconsideration"],
    ),
    Source(
        doc_id="poms_gn_03102_200_reconsideration_dismissal",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203102200",
        source_type="POMS Appeals",
        title="POMS GN 03102.200: Dismissal of a Request for Reconsideration",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["reconsideration"],
    ),
    Source(
        doc_id="poms_gn_03102_225_ssa_561_reconsideration",
        url="https://secure.ssa.gov/apps10/poms.nsf/links/0203102225",
        source_type="POMS Form Guidance",
        title="POMS GN 03102.225: Preparation of Form SSA-561 Request for Reconsideration",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["reconsideration"],
    ),
    Source(
        doc_id="poms_gn_03102_250_ssa_561_reconsideration_form",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203102250",
        source_type="POMS Form Guidance",
        title="POMS GN 03102.250: Form SSA-561-U2 Request for Reconsideration",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["reconsideration"],
    ),
    Source(
        doc_id="poms_gn_03102_300_field_office_reconsideration_development",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203102300",
        source_type="POMS Appeals",
        title="POMS GN 03102.300: Field Office Reconsideration Development",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["reconsideration"],
    ),
    Source(
        doc_id="poms_gn_03103_010_hearing_process",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203103010",
        source_type="POMS Appeals",
        title="POMS GN 03103.010: Hearing Process",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["hearing"],
    ),
    Source(
        doc_id="poms_gn_03103_020_ha_501_hearing_request",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0203103020",
        source_type="POMS Form Guidance",
        title="POMS GN 03103.020: HA-501-U5 Request for Hearing by Administrative Law Judge",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["hearing"],
    ),
    Source(
        doc_id="poms_gn_03103_080_forwarding_hearing_request",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0203103080",
        source_type="POMS Form Guidance",
        title="POMS GN 03103.080: Forwarding HA-501-U5 Hearing Request",
        index="ssa_forms",
        condition_tags=[],
        appeal_stage_tags=["hearing"],
    ),
    Source(
        doc_id="poms_di_22515_025_ssa_3368_adult_disability_report",
        url="https://secure.ssa.gov/poms.nsf/lnx/0422515025",
        source_type="POMS Form Guidance",
        title="POMS DI 22515.025: Use of Form SSA-3368-BK Disability Report - Adult",
        index="ssa_forms",
        condition_tags=["medical_evidence", "work_history", "daily_activities"],
        appeal_stage_tags=["initial", "reconsideration"],
    ),
    Source(
        doc_id="poms_di_11005_055_completing_ssa_827",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0411005055",
        source_type="POMS Form Guidance",
        title="POMS DI 11005.055: Completing Form SSA-827 Authorization to Disclose Information",
        index="ssa_forms",
        condition_tags=["medical_records", "records_request", "authorization"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_11005_056_signature_requirements_ssa_827",
        url="https://secure.ssa.gov/poms.Nsf/lnx/0411005056",
        source_type="POMS Form Guidance",
        title="POMS DI 11005.056: Signature Requirements for Form SSA-827",
        index="ssa_forms",
        condition_tags=["medical_records", "records_request", "authorization"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_11005_057_obtaining_ssa_827",
        url="https://secure.ssa.gov/poms.NSF/lnx/0411005057",
        source_type="POMS Form Guidance",
        title="POMS DI 11005.057: Field Office Instructions for Obtaining Form SSA-827",
        index="ssa_forms",
        condition_tags=["medical_records", "records_request", "authorization"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_ha_01110_010_appointing_representative",
        url="https://secure.ssa.gov/poms.nsf/lnx/2501110010",
        source_type="POMS Representation",
        title="POMS HA 01110.010: Appointing a Representative",
        index="ssa_forms",
        condition_tags=["advocate", "representative"],
        appeal_stage_tags=["reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_gn_03905_030_ssa_1696_forms",
        url="https://secure.ssa.gov/poms.nsf/lnx/0203905030",
        source_type="POMS Representation",
        title="POMS GN 03905.030: Forms SSA-1696 Appointment, Revocation, and Withdrawal",
        index="ssa_forms",
        condition_tags=["advocate", "representative"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_gn_03910_040_appointment_representative",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0203910040",
        source_type="POMS Representation",
        title="POMS GN 03910.040: Appointment of a Representative",
        index="ssa_forms",
        condition_tags=["advocate", "representative"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_ha_01210_080_right_to_representation",
        url="https://secure.ssa.gov/poms.nsf/lnx/2501210080",
        source_type="POMS Representation",
        title="POMS HA 01210.080: The Right to Representation",
        index="ssa_forms",
        condition_tags=["advocate", "representative", "hearing"],
        appeal_stage_tags=["hearing"],
    ),
    Source(
        doc_id="poms_di_34005_101_musculoskeletal_listings",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0434005101",
        source_type="POMS Listing",
        title="POMS DI 34005.101: Musculoskeletal Disorders",
        index="ssa_policy",
        condition_tags=["musculoskeletal", "listings"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_34001_032_mental_disorders",
        url="https://secure.ssa.gov/apps10/poms.nsf/lnx/0434001032",
        source_type="POMS Listing",
        title="POMS DI 34001.032: Mental Disorders",
        index="ssa_policy",
        condition_tags=["mental_limitations", "concentration_persistence_pace", "listings"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
    Source(
        doc_id="poms_di_24583_005_psychiatric_review_technique",
        url="https://secure.ssa.gov/poms.nsf/lnx/0424583005",
        source_type="POMS Mental Evidence",
        title="POMS DI 24583.005: Evaluating Mental Impairments Using the Psychiatric Review Technique",
        index="ssa_policy",
        condition_tags=["mental_limitations", "concentration_persistence_pace", "paragraph_b"],
        appeal_stage_tags=["initial", "reconsideration", "hearing"],
    ),
]


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.skip_depth = 0
        self.in_title = False
        self.current_heading: str | None = None
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in {"h1", "h2", "h3"}:
            self.current_heading = tag
            self.parts.append("\n")
        if tag in {"p", "br", "div", "li", "tr", "section", "article", "header"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in {"h1", "h2", "h3"}:
            self.current_heading = None
            self.parts.append("\n")
        if tag in {"p", "li", "tr", "section", "article"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = clean_inline(data)
        if not text:
            return
        if self.in_title:
            self.title_parts.append(text)
        if self.current_heading:
            self.headings.append(text)
        self.parts.append(text)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))

    def title(self) -> str:
        return normalize_text(" ".join(self.title_parts))


def clean_inline(value: str) -> str:
    value = html.unescape(value)
    value = repair_mojibake(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_text(value: str) -> str:
    value = html.unescape(value)
    value = repair_mojibake(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*", "\n", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip()


def repair_mojibake(value: str) -> str:
    replacements = {
        "â€œ": '"',
        "â€": '"',
        "â€˜": "'",
        "â€™": "'",
        "â€”": "-",
        "â€“": "-",
        "â€¢": "•",
        "Â§": "§",
        "Â ": " ",
    }
    for bad, good in replacements.items():
        value = value.replace(bad, good)
    return value


def fetch(url: str, timeout: int = 30) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "DignityMachineHackathonBot/0.1 (+https://rapid-agent.devpost.com/)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def safe_filename(doc_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", doc_id) + ".html"


def parse_html(raw: bytes) -> tuple[str, str]:
    text = raw.decode("utf-8", errors="replace")
    parser = VisibleTextParser()
    parser.feed(text)
    return parser.title(), parser.text()


def chunk_text(text: str, max_words: int = 360, overlap_words: int = 45) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(end - overlap_words, start + 1)
    return chunks


def stable_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def make_records(source: Source, title: str, text: str, retrieved_at: str) -> list[dict]:
    title = title or source.title
    chunks = chunk_text(text)
    records: list[dict] = []
    for idx, chunk in enumerate(chunks):
        chunk_id = f"{source.doc_id}_chunk_{idx:03d}"
        section = infer_section(chunk) or title
        records.append(
            {
                "doc_id": source.doc_id,
                "chunk_id": chunk_id,
                "source_type": source.source_type,
                "title": title,
                "section": section,
                "url": source.url,
                "retrieved_at": retrieved_at,
                "content": chunk,
                "chunk_index": idx,
                "condition_tags": source.condition_tags,
                "appeal_stage_tags": source.appeal_stage_tags,
                "embedding_text": f"{title}\n{section}\n{chunk}",
                "content_sha1": stable_hash(chunk),
            }
        )
    return records


def infer_section(chunk: str) -> str | None:
    match = re.search(r"((?:SSR|DI|HALLEX|Listing|Section|Sec\.|§)\s+[A-Za-z0-9.\-]+[^.]{0,90})", chunk)
    if match:
        return normalize_text(match.group(1))
    sentence = chunk.split(".")[0].strip()
    if 12 <= len(sentence) <= 120:
        return sentence
    return None


def write_jsonl(path: Path, records: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def scrape_source(source: Source, use_cache: bool) -> tuple[list[dict], dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / safe_filename(source.doc_id)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    try:
        if use_cache and raw_path.exists():
            raw = raw_path.read_bytes()
            status = "cached"
        else:
            raw = fetch(source.url)
            raw_path.write_bytes(raw)
            status = "fetched"
        parsed_title, text = parse_html(raw)
        if len(text.split()) < 40:
            raise ValueError(f"extracted text too short ({len(text.split())} words)")
        records = make_records(source, parsed_title or source.title, text, retrieved_at)
        return records, {
            "doc_id": source.doc_id,
            "url": source.url,
            "index": source.index,
            "status": status,
            "chunks": len(records),
            "words": len(text.split()),
            "raw_path": str(raw_path.relative_to(ROOT)),
        }
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return [], {
            "doc_id": source.doc_id,
            "url": source.url,
            "index": source.index,
            "status": "failed",
            "error": str(exc),
            "chunks": 0,
        }


def run(use_cache: bool) -> int:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict]] = {}
    manifest: list[dict] = []

    for source in SOURCES:
        print(f"scraping {source.doc_id} ...", flush=True)
        records, summary = scrape_source(source, use_cache=use_cache)
        manifest.append(summary)
        grouped.setdefault(source.index, []).extend(records)
        print(f"  {summary['status']} {summary.get('chunks', 0)} chunks", flush=True)

    counts = {
        index: write_jsonl(PROCESSED_DIR / f"{index}.jsonl", records)
        for index, records in sorted(grouped.items())
    }
    manifest_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(SOURCES),
        "counts": counts,
        "sources": manifest,
    }
    (PROCESSED_DIR / "scrape_manifest.json").write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    failed = [item for item in manifest if item["status"] == "failed"]
    print(json.dumps({"counts": counts, "failed": failed}, indent=2), flush=True)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape official SSA pages into Elastic-ready JSONL.")
    parser.add_argument("--no-cache", action="store_true", help="Refetch pages even if raw HTML exists.")
    args = parser.parse_args()
    return run(use_cache=not args.no_cache)


if __name__ == "__main__":
    sys.exit(main())
