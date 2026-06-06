from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "documents" / "example-denial.pdf"


PAGES = [
    [
        "Social Security Administration",
        "Notice of Disability Decision",
        "",
        "Date: March 18, 2024",
        "Claimant: Example Claimant",
        "Claim Type: Disability Insurance Benefits",
        "Condition Reviewed: Fibromyalgia",
        "",
        "We have reviewed your claim for disability benefits. Based on the medical",
        "and other information currently in your file, we have determined that you",
        "are not disabled under our rules.",
        "",
        "Why We Made This Decision",
        "",
        "Your records show that you have been treated for fibromyalgia, including",
        "reports of widespread pain, fatigue, poor sleep, and difficulty concentrating.",
        "We considered these symptoms when reviewing your claim.",
        "",
        "However, the evidence in your file does not show that your condition prevents",
        "you from doing all work activity on a regular and continuing basis. The",
        "records do not include a treating doctor statement explaining your limits",
        "with sitting, standing, walking, lifting, staying on task, or attending work",
        "on a consistent schedule.",
        "",
        "We also did not receive complete follow-up treatment notes for the recent",
        "period referenced in your file. Without those records, we could not confirm",
        "the frequency and severity of your symptoms over time.",
        "",
        "Evidence We Reviewed",
        "",
        "- Application for disability benefits",
        "- Adult Function Report",
        "- Primary care treatment notes",
        "- Rheumatology treatment note dated January 12, 2024",
        "- Medication list submitted with your claim",
        "- Work history information submitted with your claim",
    ],
    [
        "Social Security Administration",
        "Notice of Disability Decision - Continued",
        "",
        "What We Found",
        "",
        "The medical evidence supports that you have a medically documented condition.",
        "The evidence does not currently show enough detail about how the condition",
        "limits your ability to function during a normal workday and workweek.",
        "",
        "The file would need more information about:",
        "",
        "- How long you can sit, stand, and walk during a normal day",
        "- How much you can lift or carry",
        "- Whether pain, fatigue, or medication side effects affect concentration",
        "- How often symptoms would cause missed work or extra breaks",
        "- Whether recent follow-up visits show ongoing severe symptoms",
        "",
        "Your Right To Appeal",
        "",
        "If you disagree with this decision, you may ask us to review your claim again.",
        "You must request an appeal within 60 days from the date you receive this",
        "notice. You may submit additional medical records, doctor statements, or other",
        "information that explains how your condition affects your ability to work.",
        "",
        "If you have questions, contact your local Social Security office or a trusted",
        "representative before sending new information.",
        "",
        "This notice is based on the information currently available in your file.",
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
