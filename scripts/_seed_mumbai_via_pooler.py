"""Seed Mumbai DB via jakkas_app pooler connection from dumped Tokyo JSON."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "scripts/_mumbai_seed_data.json").read_text(encoding="utf-8"))

PW = "JakkasMumbaiApp#9Kx7mQ2pLv"
REF = "mtaowfwuuggkdcnzodfa"
DSN = (
    f"postgresql://jakkas_app.{REF}:{quote(PW, safe='')}"
    f"@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
)

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

JSONB_HINTS = {
    "permissions_json",
    "amenities",
    "amenities_json",
    "images_json",
    "videos_json",
    "meta",
    "meta_json",
    "property_ids",
}


def main() -> int:
    conn = psycopg2.connect(DSN, connect_timeout=15)
    conn.autocommit = False
    cur = conn.cursor()
    # Clear dependents first
    for table in reversed(ORDER):
        cur.execute(f"DELETE FROM {table}")
    for table in ORDER:
        rows = DATA.get(table) or []
        if not rows:
            print(f"{table}: 0")
            continue
        cols = list(rows[0].keys())
        col_list = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
        values = []
        for row in rows:
            vals = []
            for c in cols:
                v = row.get(c)
                if c in JSONB_HINTS and v is not None and not isinstance(v, (dict, list)):
                    # already plain
                    pass
                if c in JSONB_HINTS and isinstance(v, (dict, list)):
                    v = Json(v)
                vals.append(v)
            values.append(tuple(vals))
        psycopg2.extras.execute_batch(cur, sql, values, page_size=100)
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE((SELECT MAX(id) FROM {table}), 1))",
            (table,),
        )
        print(f"{table}: {len(rows)}")
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM properties"); print("properties_count", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM testimonials"); print("testimonials_count", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM admins"); print("admins_count", cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM inquiries"); print("inquiries_count", cur.fetchone()[0])
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
