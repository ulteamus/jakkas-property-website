import json
from datetime import date, timedelta

from database import execute, query_all, query_one
from database.db import use_sqlite

_schema_checked = False


def _ensure_table():
    if use_sqlite():
        execute(
            """CREATE TABLE IF NOT EXISTS owner_submissions (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               property_id INTEGER,
               owner_name TEXT NOT NULL,
               owner_mobile TEXT NOT NULL,
               owner_alt_mobile TEXT,
               owner_email TEXT,
               owner_address TEXT NOT NULL,
               property_title TEXT NOT NULL,
               property_type TEXT NOT NULL,
               property_status TEXT NOT NULL,
               bhk INTEGER DEFAULT 0,
               bungalow_number TEXT,
               area_sq_ft REAL,
               price REAL,
               property_address TEXT NOT NULL,
               city TEXT DEFAULT 'Surat',
               location_area TEXT,
               description TEXT,
               amenities_json TEXT,
               listing_intent TEXT DEFAULT 'buy',
               images_json TEXT,
               videos_json TEXT,
               status TEXT DEFAULT 'pending',
               owner_admin_id INTEGER,
               reviewed_by INTEGER,
               reviewed_at TEXT,
               review_note TEXT,
               created_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        _ensure_schema()
        return

    execute(
        """CREATE TABLE IF NOT EXISTS owner_submissions (
           id INT AUTO_INCREMENT PRIMARY KEY,
           property_id INT,
           owner_name VARCHAR(160) NOT NULL,
           owner_mobile VARCHAR(30) NOT NULL,
           owner_alt_mobile VARCHAR(30),
           owner_email VARCHAR(180),
           owner_address TEXT NOT NULL,
           property_title VARCHAR(220) NOT NULL,
           property_type VARCHAR(80) NOT NULL,
           property_status VARCHAR(40) NOT NULL,
           bhk INT DEFAULT 0,
           bungalow_number VARCHAR(80),
           area_sq_ft DECIMAL(12,2),
           price DECIMAL(15,2),
           property_address TEXT NOT NULL,
           city VARCHAR(100) DEFAULT 'Surat',
           location_area VARCHAR(150),
           description TEXT,
           amenities_json TEXT,
           listing_intent VARCHAR(20) DEFAULT 'buy',
           images_json LONGTEXT,
           videos_json LONGTEXT,
           status VARCHAR(30) DEFAULT 'pending',
           owner_admin_id INT NULL,
           reviewed_by INT NULL,
           reviewed_at TIMESTAMP NULL,
           review_note TEXT,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           INDEX idx_submission_property_id (property_id)
        )"""
    )
    _ensure_schema()


def _ensure_schema():
    global _schema_checked
    if _schema_checked:
        return
    _schema_checked = True

    if use_sqlite():
        cols = {str(row.get("name", "")).lower() for row in query_all("PRAGMA table_info(owner_submissions)")}
        if "owner_admin_id" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN owner_admin_id INTEGER")
        if "reviewed_by" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN reviewed_by INTEGER")
        if "reviewed_at" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN reviewed_at TEXT")
        if "review_note" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN review_note TEXT")
        if "apartment_number" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN apartment_number TEXT")
        if "submitter_type" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN submitter_type TEXT DEFAULT 'owner'")
        if "area_unit" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN area_unit TEXT")
        if "area_value" not in cols:
            execute("ALTER TABLE owner_submissions ADD COLUMN area_value REAL")
        return

    cols = {str(row.get("Field", "")).lower() for row in query_all("SHOW COLUMNS FROM owner_submissions")}
    if "owner_admin_id" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN owner_admin_id INT NULL")
    if "reviewed_by" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN reviewed_by INT NULL")
    if "reviewed_at" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN reviewed_at TIMESTAMP NULL")
    if "review_note" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN review_note TEXT")
    if "apartment_number" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN apartment_number VARCHAR(80)")
    if "submitter_type" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN submitter_type VARCHAR(20) DEFAULT 'owner'")
    if "area_unit" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN area_unit VARCHAR(20)")
    if "area_value" not in cols:
        execute("ALTER TABLE owner_submissions ADD COLUMN area_value DECIMAL(12,2)")


def _decode_json(raw):
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, str):
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _parse_submission(row):
    if not row:
        return None
    row["amenities"] = _decode_json(row.get("amenities_json"))
    row["images"] = _decode_json(row.get("images_json"))
    row["videos"] = _decode_json(row.get("videos_json"))
    return row


def create_submission(data):
    _ensure_table()
    owner_admin_id = data.get("owner_admin_id")
    if not owner_admin_id and data.get("property_id"):
        prop = query_one(
            "SELECT owner_admin_id FROM properties WHERE id=%s LIMIT 1",
            (data.get("property_id"),),
        )
        owner_admin_id = (prop or {}).get("owner_admin_id")
    if not owner_admin_id:
        from models.admin import Admin

        owner_admin_id = Admin.get_default_owner_admin_id()
    return execute(
        """INSERT INTO owner_submissions (
           property_id, owner_name, owner_mobile, owner_alt_mobile, owner_email, owner_address,
           property_title, property_type, property_status, bhk, bungalow_number, apartment_number,
           area_sq_ft, area_unit, area_value, price, property_address, city, location_area, description,
           amenities_json, listing_intent, images_json, videos_json, status, owner_admin_id, submitter_type
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            data.get("property_id"),
            data["owner_name"],
            data["owner_mobile"],
            data.get("owner_alt_mobile"),
            data.get("owner_email"),
            data["owner_address"],
            data["property_title"],
            data["property_type"],
            data.get("property_status", "buy"),
            int(data.get("bhk") or 0),
            data.get("bungalow_number"),
            data.get("apartment_number"),
            float(data.get("area_sq_ft") or 0),
            data.get("area_unit"),
            float(data.get("area_value") or 0) or None,
            float(data.get("price") or 0),
            data["property_address"],
            data.get("city", "Surat"),
            data.get("location_area"),
            data.get("description"),
            json.dumps(data.get("amenities") or []),
            data.get("listing_intent", "buy"),
            json.dumps(data.get("images") or []),
            json.dumps(data.get("videos") or []),
            "pending",
            owner_admin_id,
            (data.get("submitter_type") or "owner").lower(),
        ),
    )


def recent_submissions(limit=50):
    _ensure_table()
    rows = query_all(
        "SELECT * FROM owner_submissions ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
    return [_parse_submission(row) for row in rows]


def list_submissions(status=None, limit=200, offset=0, owner_admin_id=None, start_date=None, end_date=None, area=None):
    _ensure_table()
    sql = (
        """SELECT s.*, p.status AS property_current_status, p.slug AS property_slug
           FROM owner_submissions s
           LEFT JOIN properties p ON p.id=s.property_id
           WHERE 1=1"""
    )
    params = []
    if status:
        sql += " AND s.status=%s"
        params.append(status)
    if owner_admin_id:
        sql += " AND s.owner_admin_id=%s"
        params.append(owner_admin_id)
    if start_date:
        sql += " AND DATE(s.created_at) >= DATE(%s)"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(s.created_at) <= DATE(%s)"
        params.append(end_date)
    if area:
        sql += " AND (LOWER(COALESCE(s.location_area,'')) LIKE %s OR LOWER(COALESCE(s.property_address,'')) LIKE %s OR LOWER(COALESCE(s.city,'')) LIKE %s)"
        like = f"%{str(area).strip().lower()}%"
        params.extend([like, like, like])
    sql += (
        """ ORDER BY
            CASE
              WHEN s.status='pending' THEN 0
              WHEN s.status='approved' THEN 1
              ELSE 2
            END,
            s.created_at DESC
            LIMIT %s OFFSET %s"""
    )
    params.extend([limit, offset])
    rows = query_all(sql, params)
    return [_parse_submission(row) for row in rows]


def get_submission(submission_id, owner_admin_id=None):
    _ensure_table()
    sql = (
        """SELECT s.*, p.status AS property_current_status, p.slug AS property_slug
           FROM owner_submissions s
           LEFT JOIN properties p ON p.id=s.property_id
           WHERE s.id=%s"""
    )
    params = [submission_id]
    if owner_admin_id:
        sql += " AND s.owner_admin_id=%s"
        params.append(owner_admin_id)
    row = query_one(
        sql,
        params,
    )
    return _parse_submission(row)


def latest_for_property_ids(property_ids, status=None):
    _ensure_table()
    ids = [int(pid) for pid in property_ids if pid]
    if not ids:
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    sql = (
        "SELECT * FROM owner_submissions "
        f"WHERE property_id IN ({placeholders})"
    )
    params = list(ids)
    if status:
        sql += " AND status=%s"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    rows = query_all(sql, params)

    mapping = {}
    for row in rows:
        pid = row.get("property_id")
        if pid not in mapping:
            mapping[pid] = _parse_submission(row)
    return mapping


def count_by_status(status="pending", owner_admin_id=None):
    _ensure_table()
    if owner_admin_id:
        row = query_one(
            "SELECT COUNT(*) AS c FROM owner_submissions WHERE status=%s AND owner_admin_id=%s",
            (status, owner_admin_id),
        )
    else:
        row = query_one("SELECT COUNT(*) AS c FROM owner_submissions WHERE status=%s", (status,))
    return int((row or {}).get("c") or 0)


def set_submission_status(submission_id, status, reviewed_by=None, review_note=None):
    _ensure_table()
    clean_status = (status or "").strip().lower()
    if clean_status not in {"pending", "approved", "rejected"}:
        raise ValueError("Invalid submission status.")
    execute(
        """UPDATE owner_submissions
           SET status=%s, reviewed_by=%s, reviewed_at=NOW(), review_note=%s
           WHERE id=%s""",
        (
            clean_status,
            reviewed_by,
            (review_note or "").strip() or None,
            submission_id,
        ),
    )


def mark_submission_status(submission_id, status):
    set_submission_status(submission_id, status)


def _period_bounds(period_key):
    today = date.today()
    key = (period_key or "weekly").strip().lower()
    if key in {"daily", "day"}:
        return key if key == "daily" else "daily", today, today
    if key in {"monthly", "month"}:
        return "monthly", today.replace(day=1), today
    if key in {"yearly", "year"}:
        return "yearly", today.replace(month=1, day=1), today
    return "weekly", today - timedelta(days=6), today


def count_in_range(start_date, end_date, status=None, owner_admin_id=None):
    _ensure_table()
    sql = "SELECT COUNT(*) AS c FROM owner_submissions WHERE 1=1"
    params = []
    if status:
        sql += " AND status=%s"
        params.append(status)
    if owner_admin_id:
        sql += " AND owner_admin_id=%s"
        params.append(owner_admin_id)
    if start_date:
        sql += " AND DATE(created_at) >= DATE(%s)"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(created_at) <= DATE(%s)"
        params.append(end_date)
    row = query_one(sql, params)
    return int((row or {}).get("c") or 0)


def period_counts(owner_admin_id=None):
    periods = {}
    for key in ("daily", "weekly", "monthly", "yearly"):
        _, start, end = _period_bounds(key)
        periods[key] = count_in_range(start.isoformat(), end.isoformat(), owner_admin_id=owner_admin_id)
    return periods


def update_submission(submission_id, data):
    _ensure_table()
    execute(
        """UPDATE owner_submissions SET
           owner_name=%s, owner_mobile=%s, owner_alt_mobile=%s, owner_email=%s, owner_address=%s,
           property_title=%s, property_type=%s, property_status=%s, bhk=%s, bungalow_number=%s,
           area_sq_ft=%s, price=%s, property_address=%s, city=%s, location_area=%s, description=%s,
           amenities_json=%s, listing_intent=%s, review_note=%s
           WHERE id=%s""",
        (
            data["owner_name"],
            data["owner_mobile"],
            data.get("owner_alt_mobile"),
            data.get("owner_email"),
            data["owner_address"],
            data["property_title"],
            data["property_type"],
            data.get("property_status", "sell"),
            int(data.get("bhk") or 0),
            data.get("bungalow_number"),
            float(data.get("area_sq_ft") or 0),
            float(data.get("price") or 0),
            data["property_address"],
            data.get("city", "Surat"),
            data.get("location_area"),
            data.get("description"),
            json.dumps(data.get("amenities") or []),
            data.get("listing_intent", "buy"),
            (data.get("review_note") or "").strip() or None,
            submission_id,
        ),
    )


def delete_submission(submission_id):
    _ensure_table()
    execute("DELETE FROM owner_submissions WHERE id=%s", (submission_id,))
