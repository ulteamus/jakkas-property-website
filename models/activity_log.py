import json

from database import execute, query_all
from database.db import use_sqlite

_schema_checked = False


def _ensure_schema():
    global _schema_checked
    if _schema_checked:
        return
    _schema_checked = True
    if use_sqlite():
        execute(
            """CREATE TABLE IF NOT EXISTS activity_logs (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               admin_id INTEGER,
               action_key TEXT NOT NULL,
               action_label TEXT NOT NULL,
               entity_type TEXT,
               entity_id INTEGER,
               meta_json TEXT,
               created_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        return
    execute(
        """CREATE TABLE IF NOT EXISTS activity_logs (
           id BIGINT AUTO_INCREMENT PRIMARY KEY,
           admin_id INT NULL,
           action_key VARCHAR(120) NOT NULL,
           action_label VARCHAR(220) NOT NULL,
           entity_type VARCHAR(120) NULL,
           entity_id INT NULL,
           meta_json LONGTEXT NULL,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           INDEX idx_activity_logs_created_at (created_at),
           INDEX idx_activity_logs_action_key (action_key),
           INDEX idx_activity_logs_admin_id (admin_id)
        )"""
    )


def _parse_row(row):
    payload = dict(row or {})
    raw_meta = payload.get("meta_json")
    if raw_meta and isinstance(raw_meta, str):
        try:
            payload["meta"] = json.loads(raw_meta)
        except json.JSONDecodeError:
            payload["meta"] = {"raw": raw_meta}
    else:
        payload["meta"] = raw_meta or {}
    payload["admin_display"] = payload.get("full_name") or payload.get("username") or "System"
    return payload


def log_action(admin_id, action_key, action_label, entity_type=None, entity_id=None, meta=None):
    _ensure_schema()
    return execute(
        """INSERT INTO activity_logs
           (admin_id, action_key, action_label, entity_type, entity_id, meta_json)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (
            admin_id,
            (action_key or "").strip()[:120],
            (action_label or "").strip()[:220] or "Action",
            (entity_type or "").strip()[:120] or None,
            entity_id,
            json.dumps(meta or {}),
        ),
    )


def list_logs(limit=300, admin_id=None, action_key=None, start_date=None, end_date=None):
    _ensure_schema()
    sql = (
        """SELECT l.*, a.username, a.full_name
           FROM activity_logs l
           LEFT JOIN admins a ON a.id=l.admin_id
           WHERE 1=1"""
    )
    params = []
    if admin_id:
        sql += " AND l.admin_id=%s"
        params.append(admin_id)
    if action_key:
        sql += " AND l.action_key=%s"
        params.append(action_key)
    if start_date:
        sql += " AND DATE(l.created_at) >= DATE(%s)"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(l.created_at) <= DATE(%s)"
        params.append(end_date)
    sql += " ORDER BY l.created_at DESC LIMIT %s"
    params.append(max(1, min(int(limit or 300), 1000)))
    rows = query_all(sql, params)
    return [_parse_row(row) for row in rows]
