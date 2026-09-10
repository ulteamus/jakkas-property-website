"""Convert _mumbai_seed_data.json into SQL insert batches for MCP apply."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "scripts/_mumbai_seed_data.json").read_text(encoding="utf-8"))
OUT_DIR = ROOT / "scripts" / "_mumbai_seed_sql"
OUT_DIR.mkdir(exist_ok=True)

ORDER = [
    "admins",
    "properties",
    "property_images",
    "property_videos",
    "property_documents",
    "inquiries",
    "owner_submissions",
    "leads",
    "lead_notes",
    "saved_properties",
    "property_views",
    "visitors",
    "visitor_events",
    "search_analytics",
    "area_demand",
    "testimonials",
    "review_comments",
    "seller_profiles",
    "customer_visits",
    "activity_logs",
]


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, (dict, list)):
        s = json.dumps(v, ensure_ascii=False).replace("'", "''")
        return f"'{s}'::jsonb"
    s = str(v).replace("'", "''")
    return f"'{s}'"


def table_sql(table: str, rows: list[dict]) -> str:
    if not rows:
        return f"-- {table}: empty\n"
    cols = list(rows[0].keys())
    col_list = ", ".join(cols)
    lines = [f"-- {table}: {len(rows)} rows", f"DELETE FROM {table};"]
    for row in rows:
        vals = ", ".join(lit(row.get(c)) for c in cols)
        lines.append(f"INSERT INTO {table} ({col_list}) VALUES ({vals});")
    lines.append(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1));")
    return "\n".join(lines) + "\n"


def main():
    for i, table in enumerate(ORDER, 1):
        sql = table_sql(table, DATA.get(table) or [])
        path = OUT_DIR / f"{i:02d}_{table}.sql"
        path.write_text(sql, encoding="utf-8")
        print(path.name, "chars", len(sql))


if __name__ == "__main__":
    main()
