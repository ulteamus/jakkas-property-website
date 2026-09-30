"""In-app admin bell notifications and consented public lead captures."""

import re
from datetime import datetime, timezone

from database import execute, query_all, query_one

KIND_SELL_SUBMISSION = "sell_submission"
KIND_SELL_PAGE_OPEN = "sell_page_open"
KIND_LEAD_CAPTURE = "lead_capture"

BOT_UA_RE = re.compile(r"bot|crawl|spider|slurp|preview|vercel|uptime|headless|monitor|curl|wget|python-requests", re.I)
CONSENT_TEXT = "I agree to be contacted by JAKKASH Property about my property on this number."


def is_probable_bot(user_agent, accept_language=None):
    ua = (user_agent or "").strip()
    if not ua or BOT_UA_RE.search(ua):
        return True
    return not (accept_language or "").strip()


def mask_phone(phone):
    digits = re.sub(r"\D", "", str(phone or ""))
    if len(digits) < 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def create(kind, title, body=None, link=None, ref_id=None, dedupe_key=None):
    """Insert a notification; a repeated dedupe_key is silently ignored. Returns True if a row was added."""
    if dedupe_key and query_one("SELECT id FROM admin_notifications WHERE dedupe_key=%s", (dedupe_key,)):
        return False
    execute(
        """INSERT INTO admin_notifications (kind, title, body, link, ref_id, dedupe_key)
           VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (dedupe_key) DO NOTHING""",
        (kind, str(title)[:200], (str(body)[:500] if body else None), link, ref_id, dedupe_key),
    )
    return True


def hour_bucket(now=None):
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%d%H")


def notify_sell_page_open(visitor_id, now=None):
    """At most one notification per visitor per clock hour."""
    if not visitor_id:
        return False
    return create(
        KIND_SELL_PAGE_OPEN,
        "Visitor opened the Sell Property page",
        body=f"Visitor {str(visitor_id)[:8]}",
        link="/admin/analytics",
        dedupe_key=f"sell_open:{visitor_id}:{hour_bucket(now)}",
    )


def notify_sell_submission(submission_id, owner_name="", area="", property_type=""):
    details = " · ".join(bit for bit in (owner_name, property_type, area) if bit)
    return create(
        KIND_SELL_SUBMISSION,
        f"New Sell Property submission #{submission_id}",
        body=details or None,
        link="/admin/sell-properties?status=pending",
        ref_id=submission_id if isinstance(submission_id, int) else None,
        dedupe_key=f"sell_submission:{submission_id}",
    )


def record_lead_capture(phone, consent, name=None, visitor_id=None, session_id=None, source="sell_page"):
    """Store a visitor-typed phone ONLY with explicit consent. Raises ValueError otherwise."""
    from models.promotion import normalize_phone

    if consent is not True:
        raise ValueError("Consent is required before we can save your number.")
    normalized = normalize_phone(phone)
    if not normalized:
        raise ValueError("Please enter a valid 10-digit mobile number.")
    clean_name = re.sub(r"<[^>]*>", "", str(name or "")).strip()[:120] or None
    capture_id = execute(
        """INSERT INTO lead_captures (phone, name, source, consent, consent_text, visitor_id, session_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (normalized, clean_name, source, True, CONSENT_TEXT, visitor_id, session_id),
    )
    create(
        KIND_LEAD_CAPTURE,
        "Visitor shared a contact number (with consent)",
        body=f"{clean_name or 'Visitor'} · +{mask_phone(normalized)} · {source}",
        link="/admin/promotions",
        ref_id=capture_id,
        dedupe_key=f"capture:{normalized}:{hour_bucket()}",
    )
    return capture_id


def last_seen_id(admin_id):
    row = query_one("SELECT last_seen_id FROM admin_notification_state WHERE admin_id=%s", (admin_id,))
    return int((row or {}).get("last_seen_id") or 0)


def recent(limit=15):
    return [dict(r) for r in query_all(
        "SELECT id, kind, title, body, link, created_at FROM admin_notifications ORDER BY id DESC LIMIT %s",
        (int(limit),),
    ) or []]


def unread_count(admin_id):
    row = query_one(
        "SELECT COUNT(*) AS n FROM admin_notifications WHERE id > %s", (last_seen_id(admin_id),)
    )
    return int((row or {}).get("n") or 0)


def mark_seen(admin_id, up_to_id=None):
    if up_to_id is None:
        row = query_one("SELECT MAX(id) AS m FROM admin_notifications")
        up_to_id = int((row or {}).get("m") or 0)
    up_to_id = max(int(up_to_id), last_seen_id(admin_id))
    execute(
        """INSERT INTO admin_notification_state (admin_id, last_seen_id) VALUES (%s,%s)
           ON CONFLICT (admin_id) DO UPDATE SET last_seen_id=EXCLUDED.last_seen_id, updated_at=NOW()""",
        (admin_id, up_to_id),
    )
    return up_to_id


def feed(admin_id, limit=15):
    seen = last_seen_id(admin_id)
    items = recent(limit)
    for item in items:
        item["unread"] = int(item["id"]) > seen
        item["created_at"] = str(item.get("created_at") or "")[:16]
    return {"unread": unread_count(admin_id), "items": items}
