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
        extras = {
            "owner_admin_id": "INTEGER",
            "reviewed_by": "INTEGER",
            "reviewed_at": "TEXT",
            "review_note": "TEXT",
            "apartment_number": "TEXT",
            "submitter_type": "TEXT DEFAULT 'owner'",
            "area_unit": "TEXT",
            "area_value": "REAL",
            "block_wing": "TEXT",
            "unit_number": "TEXT",
            "seller_type": "TEXT",
            "listing_intent": "TEXT DEFAULT 'sell'",
        }
        for name, ddl in extras.items():
            if name not in cols:
                execute(f"ALTER TABLE owner_submissions ADD COLUMN {name} {ddl}")
        return

    cols = {str(row.get("Field", "")).lower() for row in query_all("SHOW COLUMNS FROM owner_submissions")}
    extras = {
        "owner_admin_id": "INT NULL",
        "reviewed_by": "INT NULL",
        "reviewed_at": "TIMESTAMP NULL",
        "review_note": "TEXT",
        "apartment_number": "VARCHAR(80)",
        "submitter_type": "VARCHAR(20) DEFAULT 'owner'",
        "area_unit": "VARCHAR(20)",
        "area_value": "DECIMAL(12,2)",
        "block_wing": "VARCHAR(40)",
        "unit_number": "VARCHAR(80)",
        "seller_type": "VARCHAR(20)",
        "listing_intent": "VARCHAR(20) DEFAULT 'sell'",
    }
    for name, ddl in extras.items():
        if name not in cols:
            execute(f"ALTER TABLE owner_submissions ADD COLUMN {name} {ddl}")


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


def _normalize_seller_type(value):
    cleaned = (value or "").strip().lower()
    return cleaned if cleaned in {"owner", "broker", "developer"} else "owner"


def _normalize_listing_intent(value):
    cleaned = (value or "sell").strip().lower()
    if cleaned in {"sell", "rent"}:
        return cleaned
    if cleaned in {"sale", "buy"}:
        return "sell"
    return "sell"


def format_contact_name(row):
    name = (row.get("owner_name") or "").strip() or "Unknown"
    seller = _normalize_seller_type(row.get("seller_type") or row.get("submitter_type"))
    label = seller.title()
    return f"[{label}] {name}"


def _parse_submission(row):
    if not row:
        return None
    row["amenities"] = _decode_json(row.get("amenities_json"))
    row["images"] = _decode_json(row.get("images_json"))
    row["videos"] = _decode_json(row.get("videos_json"))
    seller = _normalize_seller_type(row.get("seller_type") or row.get("submitter_type"))
    row["seller_type"] = seller
    row["submitter_type"] = seller
    row["listing_intent"] = _normalize_listing_intent(row.get("listing_intent") or row.get("property_status"))
    row["block_wing"] = (row.get("block_wing") or "").strip() or None
    unit = (row.get("unit_number") or row.get("apartment_number") or row.get("bungalow_number") or "").strip()
    row["unit_number"] = unit or None
    row["display_owner_name"] = format_contact_name(row)
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
    seller_type = _normalize_seller_type(data.get("seller_type") or data.get("submitter_type"))
    listing_intent = _normalize_listing_intent(
        data.get("listing_intent") or data.get("property_status") or "sell"
    )
    block_wing = (data.get("block_wing") or "").strip() or None
    unit_number = (
        (data.get("unit_number") or data.get("apartment_number") or data.get("bungalow_number") or "")
        .strip()
        or None
    )
    return execute(
        """INSERT INTO owner_submissions (
           property_id, owner_name, owner_mobile, owner_alt_mobile, owner_email, owner_address,
           property_title, property_type, property_status, bhk, bungalow_number, apartment_number,
           area_sq_ft, area_unit, area_value, price, property_address, city, location_area, description,
           amenities_json, listing_intent, images_json, videos_json, status, owner_admin_id,
           submitter_type, seller_type, block_wing, unit_number
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            data.get("property_id"),
            data["owner_name"],
            data["owner_mobile"],
            data.get("owner_alt_mobile"),
            data.get("owner_email"),
            data["owner_address"],
            data["property_title"],
            data["property_type"],
            data.get("property_status", listing_intent),
            int(data.get("bhk") or 0),
            data.get("bungalow_number") or unit_number,
            data.get("apartment_number") or unit_number,
            float(data.get("area_sq_ft") or 0),
            data.get("area_unit"),
            float(data.get("area_value") or 0) or None,
            float(data.get("price") or 0),
            data["property_address"],
            data.get("city", "Surat"),
            data.get("location_area"),
            data.get("description"),
            json.dumps(data.get("amenities") or []),
            listing_intent,
            json.dumps(data.get("images") or []),
            json.dumps(data.get("videos") or []),
            "pending",
            owner_admin_id,
            seller_type,
            seller_type,
            block_wing,
            unit_number,
        ),
    )


def link_property(submission_id, property_id):
    """Attach a property to a submission without deleting the submission row."""
    _ensure_table()
    execute(
        "UPDATE owner_submissions SET property_id=%s WHERE id=%s",
        (property_id, submission_id),
    )


def recent_submissions(limit=50):
    _ensure_table()
    rows = query_all(
        "SELECT * FROM owner_submissions ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
    return [_parse_submission(row) for row in rows]


def list_submissions(status=None, limit=200, offset=0, owner_admin_id=None, start_date=None, end_date=None, area=None, seller_type=None):
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
    if seller_type:
        st = _normalize_seller_type(seller_type)
        sql += " AND LOWER(COALESCE(s.seller_type, s.submitter_type, 'owner'))=%s"
        params.append(st)
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
