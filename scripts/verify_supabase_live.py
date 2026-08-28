#!/usr/bin/env python3
"""
Live Supabase health check + SQLite vs Postgres row-count verifier.

Usage:
  .\\.venv\\Scripts\\python.exe scripts/verify_supabase_live.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

DEFAULT_SQLITE = ROOT / "data" / "jakkash.db"
DEFAULT_BUCKET = "property-media"

# Logical product name → postgres table(s)
COMPARE_TABLES: list[tuple[str, str]] = [
    ("properties", "properties"),
    ("property_images", "property_images"),
    ("property_videos", "property_videos"),
    ("inquiries", "inquiries"),
    ("leads", "leads"),
    ("admins", "admins"),
    ("reviews(testimonials)", "testimonials"),
    ("reviews(review_comments)", "review_comments"),
    ("customer_visits", "customer_visits"),
    ("seller_info(seller_profiles)", "seller_profiles"),
]


def _mask_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "***")
            return parsed._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return "<redacted>" if url else "(empty)"


def sqlite_counts(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path),
        "ok": False,
        "counts": {},
        "raw_counts": {},
        "error": None,
    }
    if not path.exists():
        result["error"] = f"SQLite file missing: {path}"
        return result
    try:
        conn = sqlite3.connect(str(path))
        property_ids = {
            row[0]
            for row in conn.execute("SELECT id FROM properties").fetchall()
        }
        for label, table in COMPARE_TABLES:
            sqlite_table = table
            try:
                raw = conn.execute(f"SELECT COUNT(*) FROM {sqlite_table}").fetchone()[0]
                result["raw_counts"][label] = raw
                if table == "property_images":
                    n = conn.execute(
                        "SELECT COUNT(*) FROM property_images WHERE property_id IN (SELECT id FROM properties)"
                    ).fetchone()[0]
                elif table == "property_videos":
                    n = conn.execute(
                        "SELECT COUNT(*) FROM property_videos WHERE property_id IN (SELECT id FROM properties)"
                    ).fetchone()[0]
                else:
                    n = raw
                result["counts"][label] = n
            except sqlite3.Error as exc:
                result["counts"][label] = None
                result.setdefault("table_errors", {})[label] = str(exc)
        conn.close()
        result["ok"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def check_postgres() -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": False,
        "configured": False,
        "url_masked": "",
        "counts": {},
        "error": None,
        "select_1": None,
    }
    db_url = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    out["url_masked"] = _mask_url(db_url)
    if not db_url.startswith("postgres"):
        out["error"] = "SUPABASE_DB_URL not set (or not a postgres:// URI)"
        return out
    out["configured"] = True
    try:
        import psycopg2

        conn = psycopg2.connect(db_url, connect_timeout=15)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        out["select_1"] = cur.fetchone()[0]
        for label, table in COMPARE_TABLES:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                out["counts"][label] = cur.fetchone()[0]
            except Exception as exc:
                conn.rollback()
                out["counts"][label] = None
                out.setdefault("table_errors", {})[label] = str(exc)
        cur.close()
        conn.close()
        out["ok"] = out["select_1"] == 1
    except Exception as exc:
        out["error"] = str(exc)
        out["ok"] = False
    return out


def check_rest_api() -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": False,
        "configured": False,
        "url": (os.getenv("SUPABASE_URL") or "").strip().rstrip("/"),
        "error": None,
        "http_status": None,
    }
    url = out["url"]
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or ""
    ).strip()
    if not url or not key:
        out["error"] = "SUPABASE_URL and SUPABASE_KEY (or SERVICE_KEY) required"
        return out
    out["configured"] = True
    try:
        from supabase import create_client

        client = create_client(url, key)
        # Lightweight REST probe: list a known public table (may be empty)
        try:
            client.table("properties").select("id", count="exact").limit(1).execute()
            out["ok"] = True
            out["probe"] = "properties.select limit 1"
        except Exception as inner:
            # Auth/storage still usable even if table missing — mark partial
            out["error"] = f"REST table probe failed: {inner}"
            out["ok"] = False
            # Still try a health-ish call via storage list
            try:
                client.storage.list_buckets()
                out["ok"] = True
                out["probe"] = "storage.list_buckets (table probe failed)"
                out["warning"] = str(inner)
            except Exception as storage_exc:
                out["error"] = f"{inner} | storage: {storage_exc}"
    except Exception as exc:
        out["error"] = str(exc)
    return out


def check_storage_bucket(bucket: str = DEFAULT_BUCKET) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": False,
        "configured": False,
        "bucket": bucket,
        "exists": False,
        "error": None,
        "buckets_seen": [],
    }
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or ""
    ).strip()
    if not url or not key:
        out["error"] = "Supabase API credentials missing"
        return out
    out["configured"] = True
    try:
        from supabase import create_client

        client = create_client(url, key)
        buckets = client.storage.list_buckets() or []
        names = []
        for item in buckets:
            if isinstance(item, dict):
                names.append(item.get("name") or item.get("id"))
            else:
                names.append(getattr(item, "name", None) or getattr(item, "id", None))
        out["buckets_seen"] = [n for n in names if n]
        out["exists"] = bucket in out["buckets_seen"]
        if out["exists"]:
            # Accessibility probe — list root (empty is fine)
            try:
                client.storage.from_(bucket).list("")
                out["listable"] = True
                out["ok"] = True
            except Exception as exc:
                out["listable"] = False
                out["error"] = f"Bucket exists but list failed: {exc}"
                out["ok"] = False
        else:
            out["error"] = (
                f"Bucket '{bucket}' not found. Create a public bucket named "
                f"'{bucket}' in Dashboard → Storage."
            )
    except Exception as exc:
        out["error"] = str(exc)
    return out


def compare_counts(sqlite_side: dict[str, Any], pg_side: dict[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {"match_all": False, "rows": []}
    all_match = True
    sq = sqlite_side.get("counts") or {}
    pg = pg_side.get("counts") or {}
    for label, _table in COMPARE_TABLES:
        s = sq.get(label)
        p = pg.get(label)
        match = s is not None and p is not None and s == p
        if not match:
            all_match = False
        comparison["rows"].append(
            {
                "table": label,
                "sqlite": s,
                "postgres": p,
                "match": match,
            }
        )
    comparison["match_all"] = all_match and bool(pg) and pg_side.get("ok")
    return comparison


def run_verify(sqlite_path: Path, bucket: str) -> dict[str, Any]:
    report: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "sqlite": sqlite_counts(sqlite_path),
        "postgres": check_postgres(),
        "rest_api": check_rest_api(),
        "storage": check_storage_bucket(bucket),
    }
    report["count_comparison"] = compare_counts(report["sqlite"], report["postgres"])
    report["overall_ok"] = bool(
        report["postgres"].get("ok")
        and report["rest_api"].get("ok")
        and report["storage"].get("ok")
        and report["count_comparison"].get("match_all")
    )
    # Partial connectivity without data match still useful
    report["connectivity_ok"] = bool(
        report["postgres"].get("ok")
        and report["rest_api"].get("ok")
        and report["storage"].get("ok")
    )
    return report


def print_report(report: dict[str, Any]) -> None:
    print("=" * 64)
    print("Supabase live verification")
    print("=" * 64)
    print(f"Checked at: {report.get('checked_at')}")
    print()

    pg = report["postgres"]
    print("[Database - PostgreSQL]")
    print(f"  Configured: {pg.get('configured')}")
    print(f"  URL:        {pg.get('url_masked')}")
    print(f"  SELECT 1:   {pg.get('select_1')}")
    print(f"  Status:     {'OK' if pg.get('ok') else 'FAIL'}")
    if pg.get("error"):
        print(f"  Error:      {pg['error']}")
    print()

    api = report["rest_api"]
    print("[REST API]")
    print(f"  Configured: {api.get('configured')}")
    print(f"  URL:        {api.get('url') or '(empty)'}")
    print(f"  Probe:      {api.get('probe')}")
    print(f"  Status:     {'OK' if api.get('ok') else 'FAIL'}")
    if api.get("error"):
        print(f"  Error:      {api['error']}")
    if api.get("warning"):
        print(f"  Warning:    {api['warning']}")
    print()

    st = report["storage"]
    print(f"[Storage bucket - {st.get('bucket')}]")
    print(f"  Configured: {st.get('configured')}")
    print(f"  Exists:     {st.get('exists')}")
    print(f"  Listable:   {st.get('listable')}")
    print(f"  Seen:       {st.get('buckets_seen')}")
    print(f"  Status:     {'OK' if st.get('ok') else 'FAIL'}")
    if st.get("error"):
        print(f"  Error:      {st['error']}")
    print()

    print("[Row counts - SQLite (migratable) vs Postgres]")
    print(f"{'Table':<32} {'SQLite':>8} {'Postgres':>10} {'Match':>8}")
    print("-" * 64)
    raw = report["sqlite"].get("raw_counts") or {}
    for row in report["count_comparison"]["rows"]:
        s = "-" if row["sqlite"] is None else row["sqlite"]
        p = "-" if row["postgres"] is None else row["postgres"]
        m = "YES" if row["match"] else "NO"
        note = ""
        raw_n = raw.get(row["table"])
        if raw_n is not None and raw_n != row["sqlite"]:
            note = f" (raw {raw_n})"
        print(f"{row['table']:<32} {s:>8} {p:>10} {m:>8}{note}")
    print("-" * 64)
    print(
        f"Count match all: {report['count_comparison'].get('match_all')}"
    )
    print(f"Connectivity OK: {report.get('connectivity_ok')}")
    print(f"Overall OK:      {report.get('overall_ok')}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    parser.add_argument(
        "--bucket",
        default=os.getenv("SUPABASE_STORAGE_BUCKET")
        or os.getenv("SUPABASE_BUCKET")
        or DEFAULT_BUCKET,
    )
    args = parser.parse_args()

    report = run_verify(args.sqlite, args.bucket)
    print_report(report)

    out_path = ROOT / "scripts" / "_last_verify_report.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nReport JSON: {out_path}")

    # Exit 1 only on connectivity failure; row mismatch is reported but non-fatal
    if report.get("overall_ok"):
        return 0
    if report.get("connectivity_ok"):
        return 0
    if not report["postgres"].get("configured") and not report["rest_api"].get(
        "configured"
    ):
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
