from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "documents" / "maria-lopez-documents.pdf"


PAGES = [
    [
        "Maria Lopez - Disability Denial Example",
        "",
        "Demo note",
        "This example was created for a hackathon demo. It mirrors the same Maria Lopez",
        "information already saved in Elastic for the live agent run.",
        "",
        "Who this is about",
        "Name: Maria Lopez",
        "Condition: Fibromyalgia",
        "Where she is in the process: Second review after a denial",
        "Main problem: Social Security said the records do not prove how her condition",
        "affects her ability to work every day.",
        "",
        "What the agent should do",
        "1. Read the denial letter.",
        "2. Search Maria's doctor records.",
        "3. Check Social Security rules.",
        "4. Find missing proof.",
        "5. Draft a doctor records request for a human helper to review.",
    ],
    [
        "Denial Letter Summary",
        "",
        "Date: March 18, 2024",
        "Decision: Denied",
        "",
        "The denial says Maria's fibromyalgia is documented, but the file does not show",
        "enough proof of severity and work limits. The decision says the available",
        "records do not clearly explain how long Maria can sit, stand, walk, lift,",
        "focus, or keep a regular schedule.",
        "",
        "The denial also notes that the file is missing recent follow-up notes from",
        "Lakeview Rheumatology and does not include a treating doctor's statement about",
        "Maria's work limits.",
        "",
        "Plain-English issue",
        "Maria is not being denied because fibromyalgia is impossible to prove.",
        "She is being denied because the documents do not yet connect her symptoms to",
        "specific work limits in a way Social Security can review.",
    ],
    [
        "Doctor Records",
        "",
        "Lakeview Rheumatology - January 12, 2024",
        "Maria reports widespread pain, poor sleep, fatigue, and brain fog. Exam notes",
        "show widespread tenderness. The doctor continued medication and asked Maria",
        "to return in four weeks.",
        "",
        "Lakeview Rheumatology - Missing follow-up records",
        "The file mentions follow-up visits in February, March, and April 2024, but",
        "those notes are not included in the documents available for review.",
        "",
        "Primary Care Note - February 2, 2024",
        "Maria reports that pain and fatigue make it hard to sit at a desk for a full",
        "workday. The note does not estimate how long she can sit, stand, walk, lift,",
        "or stay focused.",
        "",
        "What is missing",
        "The file does not include a doctor statement that describes Maria's daily work",
        "limits in concrete terms.",
    ],
    [
        "Maria's Daily Work Limits",
        "",
        "Maria says she can sit for about 20 minutes before needing to change position.",
        "She says she can stand for about 10 minutes before pain increases. She says",
        "she has several bad days each month where fatigue and pain keep her from",
        "leaving home.",
        "",
        "Maria also reports trouble focusing when pain and sleep loss are severe.",
        "The documents describe limits with sitting, typing, focus, and keeping a",
        "regular schedule.",
        "",
        "Possible missing proof",
        "1. Treating doctor statement about sitting, standing, lifting, focus, and absences.",
        "2. February through April rheumatology notes.",
        "3. Medication side effect notes.",
        "4. Any record explaining bad days and missed-work risk.",
    ],
    [
        "Helper Contact",
        "",
        "Name: Elena Vargas",
        "Role: Disability benefits helper",
        "Email: elena.vargas@example.org",
        "",
        "What the agent can draft",
        "The agent can prepare a doctor records request asking Lakeview Rheumatology",
        "for missing follow-up notes and a doctor statement about Maria's work limits.",
        "",
        "Human review required",
        "The agent should not send anything by itself. A human should review the draft",
        "before it is sent to a doctor, helper, or agency.",
        "",
        "Elastic note",
        "This PDF is for the judge to read. The same text is already saved in Elastic",
        "so the agent can search it during the live demo.",
    ],
]


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def page_stream(lines: list[str]) -> bytes:
    parts = ["BT", "/F1 11 Tf", "50 742 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index == 0:
            parts.append("/F1 18 Tf")
            parts.append(f"({escape_pdf_text(line)}) Tj")
            parts.append("/F1 11 Tf")
        else:
            parts.append("T*")
            parts.append(f"({escape_pdf_text(line)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("ascii")


def build_pdf() -> bytes:
    objects: list[bytes] = []
    page_count = len(PAGES)
    pages_obj_id = 2
    font_obj_id = 3
    first_page_obj_id = 4
    first_stream_obj_id = first_page_obj_id + page_count

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    kids = " ".join(f"{first_page_obj_id + i} 0 R" for i in range(page_count))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    streams = [page_stream(lines) for lines in PAGES]
    for i in range(page_count):
        stream_obj = first_stream_obj_id + i
        objects.append(
            (
                f"<< /Type /Page /Parent {pages_obj_id} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
                f"/Contents {stream_obj} 0 R >>"
            ).encode("ascii")
        )

    for stream in streams:
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj_id, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")

    xref_start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f\n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n\n".encode("ascii"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(output)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(build_pdf())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
