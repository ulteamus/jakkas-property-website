import json

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
               property_ids TEXT,
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
        cols = {str(row.get("name", "")).lower() for row in query_all("PRAGMA table_info(customer_visits)")}
        if "property_ids" not in cols:
            execute("ALTER TABLE customer_visits ADD COLUMN property_ids TEXT")
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
           property_ids TEXT,
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
    cols = {str(row.get("Field", "")).lower() for row in query_all("SHOW COLUMNS FROM customer_visits")}
    if "property_ids" not in cols:
        execute("ALTER TABLE customer_visits ADD COLUMN property_ids TEXT")


def _decode_ids(raw):
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [int(x) for x in raw if str(x).isdigit() or isinstance(x, int)]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [int(x) for x in parsed if str(x).isdigit() or isinstance(x, int)]
        except json.JSONDecodeError:
            pass
        return [int(x) for x in raw.split(",") if x.strip().isdigit()]
    return []


def _parse_visit(row):
    if not row:
        return None
    ids = _decode_ids(row.get("property_ids"))
    if not ids and row.get("property_id"):
        ids = [int(row["property_id"])]
    row["property_id_list"] = ids
    names = []
    if row.get("property_name"):
        names.append(row["property_name"])
    extra = row.get("_extra_property_names") or []
    names.extend([n for n in extra if n and n not in names])
    row["property_names_display"] = ", ".join(names) if names else (
        f"Property #{ids[0]}" if ids else "—"
    )
    return row


def _base_query():
    return (
        """SELECT v.*,
                  p.property_name,
                  p.area_name
           FROM customer_visits v
           LEFT JOIN properties p ON p.id=v.property_id"""
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
    rows = [_parse_visit(r) for r in query_all(sql, params)]
    _attach_extra_property_names(rows)
    return rows


def get_visit(visit_id):
    _ensure_schema()
    row = _parse_visit(query_one(_base_query() + " WHERE v.id=%s", (visit_id,)))
    if row:
        _attach_extra_property_names([row])
    return row


def _attach_extra_property_names(rows):
    all_ids = set()
    for row in rows:
        for pid in row.get("property_id_list") or []:
            all_ids.add(pid)
    if not all_ids:
        return
    placeholders = ",".join(["%s"] * len(all_ids))
    props = {
        r["id"]: r["property_name"]
        for r in query_all(
            f"SELECT id, property_name FROM properties WHERE id IN ({placeholders})",
            tuple(all_ids),
        )
    }
    for row in rows:
        names = []
        for pid in row.get("property_id_list") or []:
            name = props.get(pid)
            if name:
                names.append(name)
        row["_extra_property_names"] = names
        row["property_names_display"] = ", ".join(names) if names else row.get("property_names_display") or "—"


def create_visit(data, created_by_admin_id=None):
    _ensure_schema()
    property_ids = _decode_ids(data.get("property_ids") or data.get("property_id_list"))
    primary_id = data.get("property_id")
    if primary_id and int(primary_id) not in property_ids:
        property_ids.insert(0, int(primary_id))
    if not primary_id and property_ids:
        primary_id = property_ids[0]
    visit_id = execute(
        """INSERT INTO customer_visits (
           visit_date, client_name, client_address, client_contact, client_requirement,
           property_id, property_ids, executive_admin_id, executive_name, executive_address, executive_contact,
           customer_signature_label, executive_signature_label,
           customer_signature_data, executive_signature_data, created_by_admin_id
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            data.get("visit_date"),
            (data.get("client_name") or "").strip()[:180],
            (data.get("client_address") or "").strip() or None,
            (data.get("client_contact") or "").strip()[:60],
            (data.get("client_requirement") or "").strip() or None,
            primary_id,
            json.dumps(property_ids) if property_ids else None,
            None,  # Linked executive removed from UI
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


def delete_visit(visit_id):
    _ensure_schema()
    execute("DELETE FROM customer_visits WHERE id=%s", (visit_id,))
