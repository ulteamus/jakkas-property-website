from database import execute, query_all, query_one
from services.lead_scoring import compute_lead_score


def create_from_inquiry(data, inquiry_id=None):
    lid = execute(
        """INSERT INTO leads (name,mobile,email,budget,preferred_area,property_id,inquiry_id,status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,'new')""",
        (
            data["name"], data["mobile"], data.get("email"), data.get("budget"),
            data.get("preferred_area"), data.get("property_id"), inquiry_id,
        ),
    )
    refresh_score(lid)
    return lid


def get_all(status=None, tier=None, urgent_only=False, limit=200):
    sql = "SELECT l.*, p.property_name FROM leads l LEFT JOIN properties p ON p.id=l.property_id WHERE 1=1"
    params = []
    if status:
        sql += " AND l.status=%s"
        params.append(status)
    if tier:
        sql += " AND l.lead_tier=%s"
        params.append(tier)
    if urgent_only:
        sql += " AND l.is_urgent=1"
    sql += " ORDER BY l.lead_score DESC, l.inquiry_date DESC LIMIT %s"
    params.append(limit)
    return query_all(sql, params)


def get_by_id(lid):
    return query_one(
        """SELECT l.*, p.property_name FROM leads l
           LEFT JOIN properties p ON p.id=l.property_id WHERE l.id=%s""",
        (lid,),
    )


def update_status(lid, status, admin_id=None):
    execute(
        "UPDATE leads SET status=%s, last_contacted_at=NOW() WHERE id=%s",
        (status, lid),
    )


def add_note(lid, note, admin_id=None, follow_up_date=None):
    execute(
        "INSERT INTO lead_notes (lead_id,admin_id,note,follow_up_date) VALUES (%s,%s,%s,%s)",
        (lid, admin_id, note, follow_up_date),
    )
    if follow_up_date:
        execute("UPDATE leads SET follow_up_date=%s WHERE id=%s", (follow_up_date, lid))


def get_notes(lid):
    return query_all(
        """SELECT ln.*, a.full_name AS admin_name FROM lead_notes ln
           LEFT JOIN admins a ON a.id=ln.admin_id WHERE lead_id=%s ORDER BY created_at DESC""",
        (lid,),
    )


def refresh_score(lid):
    lead = get_by_id(lid)
    if not lead:
        return
    score, tier = compute_lead_score(lead)
    execute(
        "UPDATE leads SET lead_score=%s, lead_tier=%s WHERE id=%s",
        (score, tier, lid),
    )


def mark_urgent_stale():
    """Leads not contacted in 24h -> urgent."""
    execute(
        """UPDATE leads SET is_urgent=1
           WHERE status='new' AND inquiry_date < NOW() - INTERVAL 24 HOUR
           AND (last_contacted_at IS NULL)"""
    )


def hot_leads(limit=10):
    return get_all(tier="hot", limit=limit)


def stats():
    return {
        "total": query_one("SELECT COUNT(*) AS c FROM leads")["c"],
        "new": query_one("SELECT COUNT(*) AS c FROM leads WHERE status='new'")["c"],
        "hot": query_one("SELECT COUNT(*) AS c FROM leads WHERE lead_tier='hot'")["c"],
        "urgent": query_one("SELECT COUNT(*) AS c FROM leads WHERE is_urgent=1")["c"],
    }
