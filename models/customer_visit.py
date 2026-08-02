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
            """CREATE TABLE IF NOT EXISTS customer_visits (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               visit_date TEXT NOT NULL,
               client_name TEXT NOT NULL,
               client_address TEXT,
               client_contact TEXT NOT NULL,
               client_requirement TEXT,
               property_id INTEGER,
               executive_admin_id INTEGER,
               executive_name TEXT,
               executive_address TEXT,
               executive_contact TEXT,
               customer_signature_label TEXT,
               executive_signature_label TEXT,
               customer_signature_data TEXT,
               executive_signature_data TEXT,
               created_by_admin_id INTEGER,
               created_at TEXT DEFAULT (datetime('now')),
               updated_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        return
    execute(
        """CREATE TABLE IF NOT EXISTS customer_visits (
           id INT AUTO_INCREMENT PRIMARY KEY,
           visit_date DATE NOT NULL,
           client_name VARCHAR(180) NOT NULL,
           client_address TEXT,
           client_contact VARCHAR(60) NOT NULL,
           client_requirement TEXT,
           property_id INT NULL,
           executive_admin_id INT NULL,
           executive_name VARCHAR(180),
           executive_address TEXT,
           executive_contact VARCHAR(60),
           customer_signature_label VARCHAR(180),
           executive_signature_label VARCHAR(180),
           customer_signature_data LONGTEXT,
           executive_signature_data LONGTEXT,
           created_by_admin_id INT NULL,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
           INDEX idx_customer_visits_visit_date (visit_date),
           INDEX idx_customer_visits_property_id (property_id),
           INDEX idx_customer_visits_executive_admin_id (executive_admin_id)
        )"""
    )


def _base_query():
    return (
        """SELECT v.*,
                  p.property_name,
                  p.area_name,
                  a.full_name AS linked_executive_name,
                  a.username AS linked_executive_username
           FROM customer_visits v
           LEFT JOIN properties p ON p.id=v.property_id
           LEFT JOIN admins a ON a.id=v.executive_admin_id"""
    )


def list_visits(limit=250, start_date=None, end_date=None):
    _ensure_schema()
    sql = _base_query() + " WHERE 1=1"
    params = []
    if start_date:
        sql += " AND DATE(v.visit_date) >= DATE(%s)"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(v.visit_date) <= DATE(%s)"
        params.append(end_date)
    sql += " ORDER BY v.visit_date DESC, v.created_at DESC LIMIT %s"
    params.append(max(1, min(int(limit or 250), 1000)))
    return query_all(sql, params)


def get_visit(visit_id):
    _ensure_schema()
    row = query_one(_base_query() + " WHERE v.id=%s", (visit_id,))
    return row


def create_visit(data, created_by_admin_id=None):
    _ensure_schema()
    visit_id = execute(
        """INSERT INTO customer_visits (
           visit_date, client_name, client_address, client_contact, client_requirement,
           property_id, executive_admin_id, executive_name, executive_address, executive_contact,
           customer_signature_label, executive_signature_label,
           customer_signature_data, executive_signature_data, created_by_admin_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            data.get("visit_date"),
            (data.get("client_name") or "").strip()[:180],
            (data.get("client_address") or "").strip() or None,
            (data.get("client_contact") or "").strip()[:60],
            (data.get("client_requirement") or "").strip() or None,
            data.get("property_id"),
            data.get("executive_admin_id"),
            (data.get("executive_name") or "").strip()[:180] or None,
            (data.get("executive_address") or "").strip() or None,
            (data.get("executive_contact") or "").strip()[:60] or None,
            (data.get("customer_signature_label") or "").strip()[:180] or None,
            (data.get("executive_signature_label") or "").strip()[:180] or None,
            (data.get("customer_signature_data") or "").strip() or None,
            (data.get("executive_signature_data") or "").strip() or None,
            created_by_admin_id,
        ),
    )
    return get_visit(visit_id)
