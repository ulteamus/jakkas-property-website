def _escape_pdf_text(value):
    text = str(value or "")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(title, lines):
    safe_lines = [str(line or "").strip() for line in (lines or []) if str(line or "").strip()]
    content_lines = ["BT", "/F1 12 Tf", "14 TL", "72 800 Td"]
    content_lines.append(f"({_escape_pdf_text(title)}) Tj")
    content_lines.append("T*")
    content_lines.append("(----------------------------------------) Tj")
    content_lines.append("T*")
    for item in safe_lines[:80]:
        content_lines.append(f"({_escape_pdf_text(item)}) Tj")
        content_lines.append("T*")
    content_lines.append("ET")
    stream_data = "\n".join(content_lines).encode("latin-1", "replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 5 0 R /Resources << /Font << /F1 4 0 R >> >> >> endobj",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
        b"5 0 obj << /Length %d >> stream\n%s\nendstream endobj" % (len(stream_data), stream_data),
    ]

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + b"\n"

    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        pdf += f"{off:010d} 00000 n \n".encode("ascii")

    pdf += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode("ascii")
    return pdf
