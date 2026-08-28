from database import execute, query_all, query_one
from database.db import skip_runtime_ddl, use_sqlite

INQUIRY_STATUSES = ["new", "contacted", "in_progress", "closed"]
INQUIRY_TYPES = ["site_visit", "general", "property"]
_schema_checked = False


def _normalize_status(value):
    cleaned = (value or "new").strip().lower()
    return cleaned if cleaned in INQUIRY_STATUSES else "new"


def _normalize_inquiry_type(value, property_id=None, source=None):
    cleaned = (value or "").strip().lower()
    if cleaned in INQUIRY_TYPES:
        return cleaned
    if cleaned in {"site_visit", "visit", "visit_request"}:
        return "site_visit"
    src = (source or "").strip().lower()
    if "visit" in src:
        return "site_visit"
    if property_id:
        return "property"
    return "general"


def _ensure_schema():
    global _schema_checked
    if _schema_checked:
        return
    _schema_checked = True
    if skip_runtime_ddl():
        return
    if use_sqlite():
        execute(
            """CREATE TABLE IF NOT EXISTS inquiries (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT NOT NULL,
               mobile TEXT NOT NULL,
               email TEXT,
               message TEXT,
               property_id INTEGER,
               source TEXT DEFAULT 'contact_form',
               status TEXT DEFAULT 'new',
               notes TEXT,
               inquiry_type TEXT DEFAULT 'general',
               created_at TEXT DEFAULT (datetime('now')),
               updated_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        cols = {str(row.get("name", "")).lower() for row in query_all("PRAGMA table_info(inquiries)")}
        for name, ddl in {
            "status": "TEXT DEFAULT 'new'",
            "notes": "TEXT",
            "updated_at": "TEXT",
            "budget": "TEXT",
            "preferred_location": "TEXT",
            "inquiry_type": "TEXT DEFAULT 'general'",
        }.items():
            if name not in cols:
                execute(f"ALTER TABLE inquiries ADD COLUMN {name} {ddl}")
        if "updated_at" not in cols:
            execute(
                "UPDATE inquiries SET updated_at=COALESCE(updated_at, created_at, datetime('now'))"
            )
        return

    execute(
        """CREATE TABLE IF NOT EXISTS inquiries (
           id INT AUTO_INCREMENT PRIMARY KEY,
           name VARCHAR(120) NOT NULL,
           mobile VARCHAR(20) NOT NULL,
           email VARCHAR(120),
           message TEXT,
           property_id INT NULL,
           source VARCHAR(50) DEFAULT 'contact_form',
           status VARCHAR(30) DEFAULT 'new',
           notes TEXT,
           inquiry_type VARCHAR(30) DEFAULT 'general',
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
           INDEX idx_inquiries_created_at (created_at),
           INDEX idx_inquiries_status (status)
        )"""
    )
    cols = {str(row.get("Field", "")).lower() for row in query_all("SHOW COLUMNS FROM inquiries")}
    for name, ddl in {
        "status": "VARCHAR(30) DEFAULT 'new'",
        "notes": "TEXT",
        "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        "budget": "VARCHAR(120)",
        "preferred_location": "VARCHAR(180)",
        "inquiry_type": "VARCHAR(30) DEFAULT 'general'",
    }.items():
        if name not in cols:
            execute(f"ALTER TABLE inquiries ADD COLUMN {name} {ddl}")


def create(data):
    _ensure_schema()
    inquiry_type = _normalize_inquiry_type(
        data.get("inquiry_type"),
        property_id=data.get("property_id"),
        source=data.get("source"),
    )
    return execute(
        """INSERT INTO inquiries (name,mobile,email,message,property_id,source,status,notes,budget,preferred_location,inquiry_type)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            data["name"],
            data["mobile"],
            data.get("email"),
            data.get("message"),
            data.get("property_id"),
            data.get("source", "contact_form"),
            _normalize_status(data.get("status")),
            data.get("notes"),
            data.get("budget"),
            data.get("preferred_location"),
            inquiry_type,
        ),
    )


def get_all(limit=150, start_date=None, end_date=None, status=None, owner_admin_id=None, inquiry_type=None):
    _ensure_schema()
    sql = (
        """SELECT i.*, p.property_name, p.owner_admin_id AS property_owner_admin_id
           FROM inquiries i
           LEFT JOIN properties p ON p.id=i.property_id
           WHERE 1=1"""
    )
    params = []
    if owner_admin_id:
        sql += " AND p.owner_admin_id=%s"
        params.append(owner_admin_id)
    if status:
        sql += " AND i.status=%s"
        params.append(_normalize_status(status))
    if inquiry_type:
        itype = _normalize_inquiry_type(inquiry_type)
        sql += " AND COALESCE(i.inquiry_type, CASE WHEN i.property_id IS NOT NULL THEN 'property' ELSE 'general' END)=%s"
        params.append(itype)
    if start_date:
        sql += " AND DATE(i.created_at) >= DATE(%s)"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(i.created_at) <= DATE(%s)"
        params.append(end_date)
    sql += " ORDER BY i.created_at DESC LIMIT %s"
    params.append(max(1, min(int(limit or 150), 1000)))
    return query_all(sql, params)


def get_by_id(inquiry_id, owner_admin_id=None):
    _ensure_schema()
    sql = (
        """SELECT i.*, p.property_name, p.owner_admin_id AS property_owner_admin_id
           FROM inquiries i
           LEFT JOIN properties p ON p.id=i.property_id
           WHERE i.id=%s"""
    )
    params = [inquiry_id]
    if owner_admin_id:
        sql += " AND p.owner_admin_id=%s"
        params.append(owner_admin_id)
    return query_one(sql, params)


def get_for_lead(lead, limit=20):
    """Inquiries related to a lead (by inquiry_id and/or mobile)."""
    _ensure_schema()
    lead = lead or {}
    rows = []
    seen = set()
    inquiry_id = lead.get("inquiry_id")
    if inquiry_id:
        row = get_by_id(inquiry_id)
        if row and row.get("id") not in seen:
            rows.append(row)
            seen.add(row["id"])
    mobile = (lead.get("mobile") or "").strip()
    if mobile:
        extras = query_all(
            """SELECT i.*, p.property_name, p.owner_admin_id AS property_owner_admin_id
               FROM inquiries i
               LEFT JOIN properties p ON p.id=i.property_id
               WHERE i.mobile=%s
               ORDER BY i.created_at DESC
               LIMIT %s""",
            (mobile, max(1, min(int(limit or 20), 50))),
        )
        for row in extras or []:
            rid = row.get("id")
            if rid in seen:
                continue
            rows.append(row)
            seen.add(rid)
    return rows


def update_entry(inquiry_id, status=None, notes=None):
    _ensure_schema()
    current = get_by_id(inquiry_id)
    if not current:
        return None
    execute(
        "UPDATE inquiries SET status=%s, notes=%s, updated_at=NOW() WHERE id=%s",
        (
            _normalize_status(status or current.get("status")),
            (notes if notes is not None else current.get("notes")),
            inquiry_id,
        ),
    )
    return get_by_id(inquiry_id)


def delete(inquiry_id):
    _ensure_schema()
    execute("DELETE FROM inquiries WHERE id=%s", (inquiry_id,))


def delete_many(inquiry_ids):
    _ensure_schema()
    ids = [int(x) for x in (inquiry_ids or []) if str(x).isdigit() or isinstance(x, int)]
    if not ids:
        return 0
    placeholders = ",".join(["%s"] * len(ids))
    execute(f"DELETE FROM inquiries WHERE id IN ({placeholders})", tuple(ids))
    return len(ids)
