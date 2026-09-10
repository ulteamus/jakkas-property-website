#!/usr/bin/env python3
"""Diagnose live API + DB DSN variants (no secret printing)."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)


def probe(path: str) -> None:
    base = "https://jakkas-property-website.vercel.app"
    try:
        with urlopen(Request(base + path, headers={"User-Agent": "diag"}), timeout=45) as r:
            body = r.read()[:500]
            print(path, r.status, body)
    except HTTPError as e:
        print(path, e.code, e.read()[:700])
    except Exception as e:
        print(path, type(e).__name__, e)


def try_dsn(label: str, dsn: str) -> None:
    import psycopg2

    u = urlparse(dsn)
    print(f"try {label} host={u.hostname} port={u.port} user={u.username} pass_len={len(u.password or '')}")
    try:
        conn = psycopg2.connect(dsn, sslmode="require", connect_timeout=20)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM properties")
        print(label, "OK", cur.fetchone())
        cur.close()
        conn.close()
    except Exception as e:
        print(label, "FAIL", type(e).__name__, str(e)[:240])


def main() -> None:
    for path in ("/api/properties", "/api/health"):
        probe(path)

    url = os.environ["SUPABASE_DB_URL"]
    u = urlparse(url)
    # raw password from URI (already decoded by urlparse)
    pw = u.password or ""
    encoded = quote(pw, safe="")
    direct = (
        f"postgresql://postgres:{encoded}@db.bvxijdsocnztgwqxqhkb.supabase.co:5432/postgres"
    )
    session_pooler = (
        f"postgresql://postgres.bvxijdsocnztgwqxqhkb:{encoded}"
        f"@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres"
    )
    try_dsn("current_env", url)
    try_dsn("direct5432", direct)
    try_dsn("session_pooler5432", session_pooler)


if __name__ == "__main__":
    main()
