from database import execute, query_all, query_one
from database.db import use_sqlite

_schema_checked = False


def _ensure_schema():
    global _schema_checked
    if _schema_checked:
        return
    _schema_checked = True
    if use_sqlite():
        execute(
            """CREATE TABLE IF NOT EXISTS seller_profiles (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               full_name TEXT NOT NULL,
               mobile TEXT NOT NULL,
               email TEXT,
               address TEXT,
               tags_text TEXT,
               notes TEXT,
               created_by_admin_id INTEGER,
               created_at TEXT DEFAULT (datetime('now')),
               updated_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        return
    execute(
        """CREATE TABLE IF NOT EXISTS seller_profiles (
           id INT AUTO_INCREMENT PRIMARY KEY,
           full_name VARCHAR(180) NOT NULL,
           mobile VARCHAR(40) NOT NULL,
           email VARCHAR(180),
           address TEXT,
           tags_text VARCHAR(600),
           notes TEXT,
           created_by_admin_id INT NULL,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
           INDEX idx_seller_profiles_mobile (mobile),
           INDEX idx_seller_profiles_created_at (created_at)
        )"""
    )


def _parse_row(row):
    payload = dict(row or {})
    tags = [item.strip() for item in str(payload.get("tags_text") or "").split(",") if item.strip()]
    payload["tags"] = tags
    return payload


def list_profiles(limit=250, keyword=None):
    _ensure_schema()
    sql = "SELECT * FROM seller_profiles WHERE 1=1"
    params = []
    if keyword:
        sql += " AND (full_name LIKE %s OR mobile LIKE %s OR email LIKE %s OR tags_text LIKE %s)"
        matcher = f"%{keyword.strip()}%"
        params.extend([matcher, matcher, matcher, matcher])
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(max(1, min(int(limit or 250), 1000)))
    rows = query_all(sql, params)
    return [_parse_row(row) for row in rows]


def get_profile(profile_id):
    _ensure_schema()
    row = query_one("SELECT * FROM seller_profiles WHERE id=%s", (profile_id,))
    return _parse_row(row) if row else None


def create_profile(data, created_by_admin_id=None):
    _ensure_schema()
    profile_id = execute(
        """INSERT INTO seller_profiles
           (full_name, mobile, email, address, tags_text, notes, created_by_admin_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (
            (data.get("full_name") or "").strip()[:180],
            (data.get("mobile") or "").strip()[:40],
            (data.get("email") or "").strip()[:180] or None,
            (data.get("address") or "").strip() or None,
            (data.get("tags_text") or "").strip()[:600] or None,
            (data.get("notes") or "").strip() or None,
            created_by_admin_id,
        ),
    )
    return get_profile(profile_id)


def update_profile(profile_id, data):
    _ensure_schema()
    execute(
        """UPDATE seller_profiles
           SET full_name=%s, mobile=%s, email=%s, address=%s, tags_text=%s, notes=%s, updated_at=NOW()
           WHERE id=%s""",
        (
            (data.get("full_name") or "").strip()[:180],
            (data.get("mobile") or "").strip()[:40],
            (data.get("email") or "").strip()[:180] or None,
            (data.get("address") or "").strip() or None,
            (data.get("tags_text") or "").strip()[:600] or None,
            (data.get("notes") or "").strip() or None,
            profile_id,
        ),
    )
    return get_profile(profile_id)
