#!/usr/bin/env python3
"""
Apply Cloud Supabase schema + storage bucket for Jakkas Property Website.

Usage:
  # Credentials via .env (USE_SQLITE=0, cloud SUPABASE_* — not 127.0.0.1)
  .\\.venv\\Scripts\\python.exe scripts\\migrate_cloud_supabase.py

  # Optional seed from local SQLite when cloud tables are empty
  .\\.venv\\Scripts\\python.exe scripts\\migrate_cloud_supabase.py --seed-from-sqlite

  # Schema only (skip storage API / seed)
  .\\.venv\\Scripts\\python.exe scripts\\migrate_cloud_supabase.py --schema-only

Never prints passwords or API keys.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

SCHEMA_PATH = ROOT / "database" / "supabase_schema.sql"
DEFAULT_BUCKET = "property-media"
DEFAULT_SQLITE = ROOT / "data" / "jakkash.db"

BUCKET_SQL = """
INSERT INTO storage.buckets (id, name, public)
VALUES (%(bucket)s, %(bucket)s, true)
ON CONFLICT (id) DO UPDATE SET public = EXCLUDED.public;
"""

# Best-effort public-read policy (ignore if already exists / permission denied).
BUCKET_POLICY_SQL = [
    """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage'
          AND tablename = 'objects'
          AND policyname = 'Public read property-media'
      ) THEN
        CREATE POLICY "Public read property-media"
        ON storage.objects FOR SELECT
        USING (bucket_id = 'property-media');
      END IF;
    END $$;
    """,
]


def _mask_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "***")
            return parsed._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return "(empty)" if not url else "<redacted>"


def _require_cloud_db_url() -> str:
    url = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
    if not url.startswith("postgres"):
        raise SystemExit(
            "SUPABASE_DB_URL missing or not a postgres:// URI. "
            "Paste the Cloud Supabase Database connection string into .env first."
        )
    host = (urlparse(url).hostname or "").lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit(
            f"SUPABASE_DB_URL points at loopback ({host}). "
            "Use the Cloud project pooler/URI (*.supabase.co), not local Docker."
        )
    if "supabase.co" not in host and "pooler.supabase" not in host:
        # Allow non-supabase hosts but warn
        print(f"WARN: DB host {host!r} is not *.supabase.co — continuing anyway.")
    return url


def _connect(url: str):
    try:
        import psycopg2
    except ImportError as exc:
        raise SystemExit("psycopg2 is required. Install: pip install psycopg2-binary") from exc
    # Prefer SSL for cloud
    connect_kwargs: dict[str, Any] = {"dsn": url}
    if "sslmode=" not in url:
        connect_kwargs["sslmode"] = "require"
    return psycopg2.connect(**connect_kwargs)


def apply_schema(conn) -> dict[str, Any]:
    if not SCHEMA_PATH.exists():
        raise SystemExit(f"Schema file missing: {SCHEMA_PATH}")
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    out: dict[str, Any] = {"path": str(SCHEMA_PATH), "ok": False, "error": None}
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        out["ok"] = True
    except Exception as exc:
        conn.rollback()
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def ensure_bucket_sql(conn, bucket: str) -> dict[str, Any]:
    out: dict[str, Any] = {"bucket": bucket, "ok": False, "error": None, "via": "sql"}
    try:
        with conn.cursor() as cur:
            cur.execute(BUCKET_SQL, {"bucket": bucket})
            for stmt in BUCKET_POLICY_SQL:
                try:
                    cur.execute(stmt)
                except Exception as pol_exc:
                    # Policy may already exist or storage schema restricted
                    out.setdefault("policy_warnings", []).append(str(pol_exc))
        conn.commit()
        out["ok"] = True
    except Exception as exc:
        conn.rollback()
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def ensure_bucket_api(bucket: str) -> dict[str, Any]:
    out: dict[str, Any] = {"bucket": bucket, "ok": False, "error": None, "via": "api"}
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY")
        or ""
    ).strip()
    if not url or not key or key == "[SENSITIVE]" or "your-" in key or "<" in key:
        out["error"] = "SUPABASE_URL / SUPABASE_KEY not configured for Storage API"
        return out
    try:
        from supabase import create_client

        client = create_client(url.rstrip("/"), key)
        existing = []
        try:
            existing = [b.get("name") or b.get("id") for b in (client.storage.list_buckets() or [])]
        except Exception:
            existing = []
        if bucket in existing:
            out["ok"] = True
            out["exists"] = True
            return out
        # supabase-py create_bucket signatures vary by version
        try:
            client.storage.create_bucket(bucket, options={"public": True})
        except TypeError:
            try:
                client.storage.create_bucket(bucket, {"public": True})
            except TypeError:
                client.storage.create_bucket(bucket)
        out["ok"] = True
        out["created"] = True
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def table_counts(conn) -> dict[str, int | None]:
    tables = [
        "admins",
        "properties",
        "property_images",
        "property_videos",
        "inquiries",
        "leads",
        "testimonials",
        "review_comments",
        "owner_submissions",
        "customer_visits",
        "seller_profiles",
    ]
    counts: dict[str, int | None] = {}
    with conn.cursor() as cur:
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = int(cur.fetchone()[0])
            except Exception:
                conn.rollback()
                counts[table] = None
    return counts


def seed_minimal_admin(conn) -> dict[str, Any]:
    """Ensure at least one admin exists (password from ADMIN_INITIAL_PASSWORD / DEFAULT_ADMIN_PASSWORD)."""
    out: dict[str, Any] = {"ok": False, "created": False}
    from werkzeug.security import generate_password_hash

    password = (
        os.getenv("ADMIN_INITIAL_PASSWORD")
        or os.getenv("DEFAULT_ADMIN_PASSWORD")
        or ""
    ).strip()
    if not password or password in {"[SENSITIVE]", "change-me-on-first-login", "admin123"}:
        # Still seed with a random password if empty DB — print once
        import secrets

        password = secrets.token_urlsafe(16)
        out["generated_password"] = password
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM admins")
            n = int(cur.fetchone()[0])
            if n > 0:
                out["ok"] = True
                out["existing"] = n
                return out
            cur.execute(
                """
                INSERT INTO admins (username, email, password_hash, full_name, role, is_active, require_otp)
                VALUES (%s, %s, %s, %s, %s, TRUE, FALSE)
                """,
                (
                    "sam",
                    "Jakkashproperty@gmail.com",
                    generate_password_hash(password),
                    "Sam",
                    "super_admin",
                ),
            )
        conn.commit()
        out["ok"] = True
        out["created"] = True
    except Exception as exc:
        conn.rollback()
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def seed_from_sqlite(sqlite_path: Path) -> dict[str, Any]:
    if not sqlite_path.exists():
        return {"ok": False, "error": f"SQLite missing: {sqlite_path}"}
    import subprocess

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "migrate_sqlite_to_supabase.py"),
        "--sqlite",
        str(sqlite_path),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate Cloud Supabase schema for Jakkas")
    parser.add_argument("--schema-only", action="store_true")
    parser.add_argument("--seed-from-sqlite", action="store_true")
    parser.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    parser.add_argument("--bucket", default=os.getenv("SUPABASE_STORAGE_BUCKET") or DEFAULT_BUCKET)
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "scripts" / "_last_cloud_migrate_report.json",
    )
    args = parser.parse_args()

    db_url = _require_cloud_db_url()
    report: dict[str, Any] = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "db_url_masked": _mask_url(db_url),
        "bucket": args.bucket,
    }

    print("=" * 64)
    print("Cloud Supabase migration")
    print("=" * 64)
    print(f"DB: {_mask_url(db_url)}")
    print(f"Schema: {SCHEMA_PATH}")

    conn = _connect(db_url)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        report["select_1"] = True
        print("SELECT 1: OK")

        schema = apply_schema(conn)
        report["schema"] = schema
        print(f"Schema apply: {'OK' if schema.get('ok') else 'FAIL'}")
        if schema.get("error"):
            print(f"  Error: {schema['error']}")
            args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 1

        bucket_sql = ensure_bucket_sql(conn, args.bucket)
        report["bucket_sql"] = bucket_sql
        print(f"Bucket SQL ({args.bucket}): {'OK' if bucket_sql.get('ok') else 'FAIL'}")
        if bucket_sql.get("error"):
            print(f"  Error: {bucket_sql['error']}")

        if not args.schema_only:
            bucket_api = ensure_bucket_api(args.bucket)
            report["bucket_api"] = bucket_api
            print(f"Bucket API ({args.bucket}): {'OK' if bucket_api.get('ok') else 'SKIP/FAIL'}")
            if bucket_api.get("error"):
                print(f"  Note: {bucket_api['error']}")

            admin = seed_minimal_admin(conn)
            report["admin_seed"] = {
                k: v for k, v in admin.items() if k != "generated_password"
            }
            if admin.get("generated_password"):
                # Write once to gitignored path — never commit
                secret_path = ROOT / "strix_runs" / "audit_report" / "CLOUD_ADMIN_PASSWORD.generated.txt"
                secret_path.parent.mkdir(parents=True, exist_ok=True)
                secret_path.write_text(
                    f"username=sam\npassword={admin['generated_password']}\n",
                    encoding="utf-8",
                )
                print(f"Admin seeded; password written to {secret_path.name} (gitignored area)")
            else:
                print(f"Admin seed: {'OK' if admin.get('ok') else 'FAIL'} existing={admin.get('existing')}")

            if args.seed_from_sqlite:
                counts_before = table_counts(conn)
                report["counts_before_seed"] = counts_before
                props = counts_before.get("properties") or 0
                if props == 0:
                    print("Seeding from SQLite (empty properties table)...")
                    seed = seed_from_sqlite(args.sqlite)
                    report["sqlite_seed"] = {
                        k: v for k, v in seed.items() if k not in {"stdout_tail", "stderr_tail"}
                    }
                    report["sqlite_seed_stdout_tail"] = seed.get("stdout_tail")
                    print(f"SQLite seed: {'OK' if seed.get('ok') else 'FAIL'}")
                else:
                    print(f"Skip SQLite seed — properties already has {props} rows")

        counts = table_counts(conn)
        report["counts"] = counts
        print("\nTable counts:")
        for name, n in counts.items():
            print(f"  {name:<22} {n if n is not None else '—'}")

        report["ok"] = bool(schema.get("ok") and (bucket_sql.get("ok") or report.get("bucket_api", {}).get("ok")))
    finally:
        conn.close()

    args.report.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nReport: {args.report}")
    print(f"Overall: {'PASS' if report.get('ok') else 'FAIL'}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
