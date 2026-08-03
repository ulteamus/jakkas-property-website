"""Pure-Python PDF helpers (no external deps) for local Windows + Vercel."""

from datetime import datetime


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 40
MARGIN_TOP = 800
LINE_HEIGHT = 14


def _escape_pdf_text(value):
    text = str(value or "")
    # Helvetica latin-1 stream: drop unsupported glyphs.
    text = text.encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _clip(value, width):
    text = " ".join(str(value or "").split())
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: max(0, width - 3)] + "..."


def _admin_label(current_user):
    if not current_user:
        return "Unknown"
    name = (
        getattr(current_user, "full_name", None)
        or getattr(current_user, "username", None)
        or "Admin"
    )
    role = getattr(current_user, "role", None) or "admin"
    return f"{name} ({role})"


def _now_stamp():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


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
    return _assemble_pdf([("\n".join(content_lines)).encode("latin-1", "replace")])


def _assemble_pdf(content_streams):
    """Build a multi-page PDF-1.4 document from content stream byte lists."""
    if not content_streams:
        content_streams = [b"BT /F1 12 Tf 72 800 Td (Empty) Tj ET"]

    objects = []
    # 1: Catalog, 2: Pages, 3: Font, then pages + contents
    font_obj_num = 3
    page_count = len(content_streams)
    first_page_obj = 4
    # Layout: Catalog(1), Pages(2), Font(3), then for each page: PageObj, ContentObj
    # Page N object number = 4 + 2*i, Content = 5 + 2*i

    page_obj_nums = [first_page_obj + (2 * i) for i in range(page_count)]
    kids = " ".join(f"{n} 0 R" for n in page_obj_nums)

    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
    objects.append(
        f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {page_count} >> endobj".encode("ascii")
    )
    objects.append(b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")

    for i, stream_data in enumerate(content_streams):
        page_num = page_obj_nums[i]
        content_num = page_num + 1
        objects.append(
            (
                f"{page_num} 0 obj << /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
                f"/Contents {content_num} 0 R "
                f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> >> endobj"
            ).encode("ascii")
        )
        objects.append(
            b"%d 0 obj << /Length %d >> stream\n%s\nendstream endobj"
            % (content_num, len(stream_data), stream_data)
        )

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


class _PdfWriter:
    def __init__(self, title="Report"):
        self.title = title
        self.pages = []
        self._ops = []
        self._y = MARGIN_TOP
        self._start_page()

    def _start_page(self):
        self._ops = ["BT", "/F1 10 Tf"]
        self._y = MARGIN_TOP
        self._ops.append(f"1 0 0 1 {MARGIN_X} {self._y} Tm")

    def _flush_page(self):
        self._ops.append("ET")
        self.pages.append("\n".join(self._ops).encode("latin-1", "replace"))
        self._ops = []

    def _ensure_space(self, lines_needed=1):
        if self._y - (LINE_HEIGHT * lines_needed) < 50:
            self._flush_page()
            self._start_page()

    def move(self, dy):
        self._y -= dy
        self._ops.append(f"0 -{dy} Td")

    def text(self, value, size=10, bold_prefix=False):
        self._ensure_space(1)
        self._ops.append(f"/F1 {size} Tf")
        self._ops.append(f"({_escape_pdf_text(value)}) Tj")
        self.move(LINE_HEIGHT if size <= 10 else LINE_HEIGHT + 2)

    def heading(self, value):
        self._ensure_space(2)
        self._ops.append("/F1 14 Tf")
        self._ops.append(f"({_escape_pdf_text(value)}) Tj")
        self.move(18)

    def rule(self):
        self.text("-" * 90, size=9)

    def blank(self):
        self.move(8)

    def finish(self):
        if self._ops:
            self._flush_page()
        return _assemble_pdf(self.pages or [b"BT /F1 12 Tf 72 800 Td (Empty) Tj ET"])


def generate_leads_list_pdf(leads, current_user, filters=None):
    """Tabular multi-lead PDF summary with export metadata header."""
    filters = filters or {}
    writer = _PdfWriter("Leads Export")
    writer.heading("JAKKASH - Leads PDF Report")
    writer.text(f"Generated: {_now_stamp()}", size=9)
    writer.text(f"Exported by: {_admin_label(current_user)}", size=9)
    filter_bits = []
    for key in ("status", "tier", "urgent_only"):
        val = filters.get(key)
        if val not in (None, "", False):
            filter_bits.append(f"{key}={val}")
    writer.text(
        f"Filters: {', '.join(filter_bits) if filter_bits else 'none (all visible)'}",
        size=9,
    )
    writer.text(f"Total leads: {len(leads or [])}", size=9)
    writer.rule()

    # Column widths in characters (approx for Helvetica 8pt)
    headers = (
        f"{'ID':<5} {'Name':<16} {'Phone':<12} {'Email':<18} "
        f"{'Property/Area':<18} {'Status':<10} {'Score':<8} {'Created':<12}"
    )
    writer.text(headers, size=8)
    writer.rule()

    for lead in leads or []:
        prop_area = lead.get("property_name") or lead.get("preferred_area") or "-"
        created = lead.get("inquiry_date") or lead.get("created_at") or "-"
        score = lead.get("lead_score")
        tier = lead.get("lead_tier") or ""
        score_tier = f"{score if score is not None else '-'}/{tier or '-'}"
        row = (
            f"{_clip(lead.get('id'), 5):<5} "
            f"{_clip(lead.get('name'), 16):<16} "
            f"{_clip(lead.get('mobile'), 12):<12} "
            f"{_clip(lead.get('email') or '-', 18):<18} "
            f"{_clip(prop_area, 18):<18} "
            f"{_clip(lead.get('status'), 10):<10} "
            f"{_clip(score_tier, 8):<8} "
            f"{_clip(created, 12):<12}"
        )
        writer.text(row, size=8)

    if not leads:
        writer.blank()
        writer.text("No leads matched the current filters.", size=10)

    writer.blank()
    writer.text("Confidential - for internal JAKKASH use only.", size=8)
    return writer.finish()


def generate_single_lead_pdf(lead, inquiries, notes, current_user):
    """1–2 page dossier for a single lead."""
    lead = lead or {}
    writer = _PdfWriter("Lead Dossier")
    writer.heading(f"JAKKASH - Lead Dossier #{lead.get('id') or '-'}")
    writer.text(f"Generated: {_now_stamp()}", size=9)
    writer.text(f"Exported by: {_admin_label(current_user)}", size=9)
    writer.rule()

    writer.text("CLIENT INFORMATION", size=11)
    writer.text(f"Name: {lead.get('name') or '-'}")
    writer.text(f"Mobile / WhatsApp: {lead.get('mobile') or '-'}")
    writer.text(f"Email: {lead.get('email') or '-'}")
    budget = lead.get("budget")
    if budget not in (None, ""):
        try:
            budget_txt = f"INR {float(budget):,.0f}"
        except (TypeError, ValueError):
            budget_txt = str(budget)
    else:
        budget_txt = "-"
    writer.text(f"Budget: {budget_txt}")
    writer.text(f"Preferred Area: {lead.get('preferred_area') or '-'}")
    writer.blank()

    writer.text("PROPERTY INTEREST", size=11)
    writer.text(f"Linked Property: {lead.get('property_name') or '-'}")
    writer.text(f"Property ID: {lead.get('property_id') or '-'}")
    writer.text(f"Source Inquiry ID: {lead.get('inquiry_id') or '-'}")
    writer.blank()

    writer.text("LEAD SCORE / STATUS", size=11)
    writer.text(f"Status: {lead.get('status') or '-'}")
    writer.text(f"Score: {lead.get('lead_score') if lead.get('lead_score') is not None else '-'}")
    writer.text(f"Tier: {lead.get('lead_tier') or '-'}")
    writer.text(f"Urgent: {'Yes' if lead.get('is_urgent') else 'No'}")
    writer.text(f"Inquiry / Created: {lead.get('inquiry_date') or lead.get('created_at') or '-'}")
    writer.text(f"Last Contacted: {lead.get('last_contacted_at') or '-'}")
    writer.text(f"Follow-up Date: {lead.get('follow_up_date') or '-'}")
    writer.blank()

    writer.text("RELATED INQUIRIES / CONTACT HISTORY", size=11)
    if inquiries:
        for inv in inquiries:
            writer.text(
                f"#{inv.get('id')} | {inv.get('created_at') or '-'} | "
                f"status={inv.get('status') or '-'} | source={inv.get('source') or '-'}"
            )
            msg = inv.get("message") or inv.get("notes") or ""
            if msg:
                writer.text(f"  {_clip(msg, 95)}", size=9)
            prop = inv.get("property_name")
            if prop:
                writer.text(f"  Property: {_clip(prop, 80)}", size=9)
    else:
        writer.text("No linked inquiry records.", size=9)
    writer.blank()

    writer.text("ADMIN NOTE HISTORY", size=11)
    if notes:
        for note in notes:
            who = note.get("admin_name") or "Admin"
            when = note.get("created_at") or "-"
            follow = note.get("follow_up_date")
            follow_bit = f" | follow-up {follow}" if follow else ""
            writer.text(f"[{when}] {who}{follow_bit}", size=9)
            writer.text(f"  {_clip(note.get('note'), 100)}", size=9)
    else:
        writer.text("No notes recorded.", size=9)

    writer.blank()
    writer.rule()
    writer.text("Confidential - for internal JAKKASH use only.", size=8)
    return writer.finish()
