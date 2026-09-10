#!/usr/bin/env python3
"""Export SQLite seed as Postgres INSERT SQL for MCP execute_sql."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

OUT = Path("scripts/_seed_cloud.sql")
DB = Path("data/jakkash.db")


def esc(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, (bytes, bytearray)):
        v = v.decode("utf-8", errors="replace")
    s = str(v).replace("'", "''")
    return f"'{s}'"


def boolish(v):
    if v is None:
        return "NULL"
    return "TRUE" if int(v) else "FALSE"


def main() -> None:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    parts: list[str] = []

    # admins
    rows = con.execute("SELECT * FROM admins").fetchall()
    for r in rows:
        cols = [c for c in r.keys()]
        # map sqlite cols that exist in PG
        keep = [
            "id",
            "username",
            "email",
            "password_hash",
            "full_name",
            "role",
            "phone",
            "is_active",
            "created_at",
        ]
        use = [c for c in keep if c in cols]
        vals = []
        for c in use:
            if c == "is_active":
                vals.append(boolish(r[c]))
            else:
                vals.append(esc(r[c]))
        parts.append(
            f"INSERT INTO admins ({', '.join(use)}) VALUES ({', '.join(vals)}) "
            "ON CONFLICT (id) DO NOTHING;"
        )

    # properties
    rows = con.execute("SELECT * FROM properties").fetchall()
    for r in rows:
        cols = set(r.keys())
        keep = [
            "id",
            "property_name",
            "slug",
            "property_type",
            "area_name",
            "address",
            "price",
            "bhk",
            "sq_ft",
            "description",
            "amenities",
            "latitude",
            "longitude",
            "status",
            "is_featured",
            "listing_type",
            "view_count",
            "primary_image",
            "creation_source",
            "listing_intent",
            "created_at",
            "updated_at",
        ]
        use = [c for c in keep if c in cols]
        vals = []
        for c in use:
            if c == "is_featured":
                vals.append(boolish(r[c]))
            elif c == "amenities":
                raw = r[c]
                if raw is None:
                    vals.append("NULL")
                else:
                    try:
                        if isinstance(raw, str):
                            json.loads(raw)
                            vals.append(esc(raw) + "::jsonb")
                        else:
                            vals.append(esc(json.dumps(raw)) + "::jsonb")
                    except Exception:
                        vals.append(esc(json.dumps([])) + "::jsonb")
            else:
                vals.append(esc(r[c]))
        parts.append(
            f"INSERT INTO properties ({', '.join(use)}) VALUES ({', '.join(vals)}) "
            "ON CONFLICT (id) DO NOTHING;"
        )

    # testimonials
    try:
        rows = con.execute("SELECT * FROM testimonials").fetchall()
    except sqlite3.Error:
        rows = []
    for r in rows:
        cols = set(r.keys())
        keep = [
            "id",
            "client_name",
            "client_location",
            "review_text",
            "rating",
            "is_active",
            "created_at",
        ]
        use = [c for c in keep if c in cols]
        vals = []
        for c in use:
            if c == "is_active":
                vals.append(boolish(r[c]))
            else:
                vals.append(esc(r[c]))
        parts.append(
            f"INSERT INTO testimonials ({', '.join(use)}) VALUES ({', '.join(vals)}) "
            "ON CONFLICT (id) DO NOTHING;"
        )

    # inquiries (sample subset if huge — we have 26)
    try:
        rows = con.execute("SELECT * FROM inquiries").fetchall()
    except sqlite3.Error:
        rows = []
    for r in rows:
        cols = set(r.keys())
        keep = [
            "id",
            "name",
            "mobile",
            "email",
            "message",
            "property_id",
            "source",
            "status",
            "notes",
            "budget",
            "preferred_location",
            "inquiry_type",
            "created_at",
            "updated_at",
        ]
        use = [c for c in keep if c in cols]
        vals = [esc(r[c]) for c in use]
        parts.append(
            f"INSERT INTO inquiries ({', '.join(use)}) VALUES ({', '.join(vals)}) "
            "ON CONFLICT (id) DO NOTHING;"
        )

    # leads
    try:
        rows = con.execute("SELECT * FROM leads").fetchall()
    except sqlite3.Error:
        rows = []
    for r in rows:
        cols = set(r.keys())
        keep = [
            "id",
            "name",
            "mobile",
            "email",
            "budget",
            "preferred_area",
            "property_id",
            "inquiry_id",
            "status",
            "lead_score",
            "lead_tier",
            "is_urgent",
            "inquiry_date",
            "created_at",
            "updated_at",
        ]
        use = [c for c in keep if c in cols]
        vals = []
        for c in use:
            if c == "is_urgent":
                vals.append(boolish(r[c]))
            else:
                vals.append(esc(r[c]))
        parts.append(
            f"INSERT INTO leads ({', '.join(use)}) VALUES ({', '.join(vals)}) "
            "ON CONFLICT (id) DO NOTHING;"
        )

    parts.append(
        "SELECT setval(pg_get_serial_sequence('admins','id'), "
        "COALESCE((SELECT MAX(id) FROM admins), 1));"
    )
    parts.append(
        "SELECT setval(pg_get_serial_sequence('properties','id'), "
        "COALESCE((SELECT MAX(id) FROM properties), 1));"
    )
    parts.append(
        "SELECT setval(pg_get_serial_sequence('testimonials','id'), "
        "COALESCE((SELECT MAX(id) FROM testimonials), 1));"
    )
    parts.append(
        "SELECT setval(pg_get_serial_sequence('inquiries','id'), "
        "COALESCE((SELECT MAX(id) FROM inquiries), 1));"
    )
    parts.append(
        "SELECT setval(pg_get_serial_sequence('leads','id'), "
        "COALESCE((SELECT MAX(id) FROM leads), 1));"
    )

    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {OUT} statements={len(parts)} chars={OUT.stat().st_size}")


if __name__ == "__main__":
    main()
