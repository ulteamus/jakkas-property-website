import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from database import execute, query_all
from utils.helpers import format_inr

from config import PROMO_COOLDOWN_DAYS, PROMO_STALE_DAYS
from models.property import PUBLIC_LISTING_STATUSES

CHANNEL_WA_LINK = "wa_link"
AUDIENCE_LIMIT = 200


def normalize_phone(value):
    """Return an Indian mobile in wa.me form (91XXXXXXXXXX) or None."""
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return "91" + digits
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return digits
    return None


def _cutoff(days, now=None):
    moment = (now or datetime.now(timezone.utc)) - timedelta(days=int(days))
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def stale_properties(stale_days=PROMO_STALE_DAYS, limit=100, now=None):
    placeholders = ",".join(["%s"] * len(PUBLIC_LISTING_STATUSES))
    rows = query_all(
        f"""SELECT id, property_name, slug, area_name, property_type, price, listing_type, bhk, created_at
            FROM properties
            WHERE LOWER(COALESCE(status,'')) IN ({placeholders})
              AND created_at IS NOT NULL AND created_at < %s
            ORDER BY created_at ASC LIMIT %s""",
        (*PUBLIC_LISTING_STATUSES, _cutoff(stale_days, now), int(limit)),
    )
    return [dict(r) for r in rows or []]


def _safe_rows(sql, params=()):
    try:
        return query_all(sql, params) or []
    except Exception:
        return []


def opted_out_phones():
    rows = _safe_rows("SELECT phone FROM whatsapp_opt_ins WHERE status=%s", ("opted_out",))
    return {normalize_phone(r.get("phone")) or r.get("phone") for r in rows}


def recently_contacted_phones(cooldown_days=PROMO_COOLDOWN_DAYS, now=None):
    rows = _safe_rows(
        "SELECT DISTINCT phone FROM whatsapp_promo_log WHERE created_at >= %s",
        (_cutoff(cooldown_days, now),),
    )
    return {r.get("phone") for r in rows if r.get("phone")}


def audience(cooldown_days=PROMO_COOLDOWN_DAYS, limit=AUDIENCE_LIMIT, now=None):
    """Lead/inquiry contacts deduped by phone, minus opt-outs and those inside the cooldown."""
    candidates = []
    for row in _safe_rows(
        "SELECT id, name, mobile, created_at FROM leads ORDER BY created_at DESC LIMIT %s", (limit * 3,)
    ):
        candidates.append(("lead", row))
    for row in _safe_rows(
        "SELECT id, name, mobile, created_at FROM inquiries ORDER BY created_at DESC LIMIT %s", (limit * 3,)
    ):
        candidates.append(("inquiry", row))

    blocked = opted_out_phones()
    cooling = recently_contacted_phones(cooldown_days, now)
    seen = set()
    eligible = []
    skipped = {"invalid": 0, "opted_out": 0, "cooldown": 0}
    for source_type, row in candidates:
        phone = normalize_phone(row.get("mobile"))
        if not phone:
            skipped["invalid"] += 1
            continue
        if phone in seen:
            continue
        seen.add(phone)
        if phone in blocked:
            skipped["opted_out"] += 1
            continue
        if phone in cooling:
            skipped["cooldown"] += 1
            continue
        eligible.append(
            {
                "phone": phone,
                "name": (row.get("name") or "").strip() or "Customer",
                "source_type": source_type,
                "source_id": row.get("id"),
            }
        )
        if len(eligible) >= limit:
            break
    return {"contacts": eligible, "skipped": skipped}


def is_eligible(phone, cooldown_days=PROMO_COOLDOWN_DAYS, now=None):
    normalized = normalize_phone(phone)
    if not normalized:
        return False
    return normalized not in opted_out_phones() and normalized not in recently_contacted_phones(cooldown_days, now)


def build_message(prop, contact_name="", base_url=""):
    greeting = f"Hi {contact_name}," if contact_name else "Hi,"
    price = format_inr(prop.get("price") or 0)
    suffix = "/month" if (prop.get("listing_type") or "") == "rent" else ""
    link = f"{base_url.rstrip('/')}/property/{prop.get('slug')}" if base_url and prop.get("slug") else ""
    lines = [
        greeting,
        f"JAKKASH Property has a listing you may like: {prop.get('property_name')} in {prop.get('area_name')}, Surat.",
        f"Price: {price}{suffix}",
    ]
    if link:
        lines.append(f"Details: {link}")
    lines.append("Reply STOP to opt out of these messages.")
    return "\n".join(lines)


def wa_link(phone, message):
    return f"https://wa.me/{phone}?text={quote(message)}"


def record_send(phone, message, contact_name=None, source_type=None, source_id=None, property_id=None, admin_id=None):
    normalized = normalize_phone(phone)
    if not normalized:
        raise ValueError("Invalid mobile number.")
    execute(
        """INSERT INTO whatsapp_promo_log
           (phone, contact_name, source_type, source_id, property_id, channel, message, sent_by_admin_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            normalized,
            (contact_name or "")[:160] or None,
            source_type,
            source_id,
            property_id,
            CHANNEL_WA_LINK,
            (message or "")[:2000],
            admin_id,
        ),
    )
    return normalized


def recent_log(limit=50):
    return [
        dict(r)
        for r in _safe_rows(
            """SELECT l.*, p.property_name FROM whatsapp_promo_log l
               LEFT JOIN properties p ON p.id = l.property_id
               ORDER BY l.created_at DESC, l.id DESC LIMIT %s""",
            (int(limit),),
        )
    ]


def set_opt_out(phone, opted_out=True, source="admin"):
    normalized = normalize_phone(phone)
    if not normalized:
        raise ValueError("Invalid mobile number.")
    status = "opted_out" if opted_out else "opted_in"
    execute(
        """INSERT INTO whatsapp_opt_ins (phone, status, source) VALUES (%s,%s,%s)
           ON CONFLICT (phone) DO UPDATE SET status=EXCLUDED.status, source=EXCLUDED.source, updated_at=NOW()""",
        (normalized, status, source),
    )
    return normalized
