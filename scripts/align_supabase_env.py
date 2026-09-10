"""Align .env to project efrbhhwdovdgxezqtpxn and pick a working Postgres DSN."""
from __future__ import annotations

import re
import socket
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

PROJECT_REF = "efrbhhwdovdgxezqtpxn"
SUPABASE_URL = f"https://{PROJECT_REF}.supabase.co"
# Legacy anon JWT from Supabase MCP get_publishable_keys (project efrbhhwdovdgxezqtpxn)
ANON_JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVmcmJoaHdkb3ZkZ3hlenF0cHhuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkwMjk4MDYsImV4cCI6MjEwNDYwNTgwNn0."
    "R_WNgZQLIQf6ArdnErmtH9ce86gw1KyETc3KhLhIEC4"
)
REGION = "ap-south-1"


def _set_env_key(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.M)
    line = f"{key}={value}"
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    if text and not text.endswith("\n"):
        text += "\n"
    return text + line + "\n"


def _dns_ok(host: str, port: int = 5432) -> bool:
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False


def _try_psycopg(dsn: str) -> tuple[bool, str]:
    try:
        import psycopg2

        conn = psycopg2.connect(dsn, connect_timeout=8)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return True, "ok"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    raw = ENV_PATH.read_text(encoding="utf-8")
    # Preserve password from existing SUPABASE_DB_URL
    m = re.search(r"^SUPABASE_DB_URL=(.*)$", raw, re.M)
    if not m:
        print("ERR: SUPABASE_DB_URL missing in .env")
        return 1
    current = m.group(1).strip().strip('"').strip("'")
    parsed = urlparse(current)
    password = unquote(parsed.password or "")
    if not password:
        print("ERR: no password in SUPABASE_DB_URL")
        return 1
    pw_enc = quote(password, safe="")

    direct = (
        f"postgresql://postgres:{pw_enc}@db.{PROJECT_REF}.supabase.co:5432/postgres"
    )
    pooler_tx = (
        f"postgresql://postgres.{PROJECT_REF}:{pw_enc}"
        f"@aws-0-{REGION}.pooler.supabase.com:6543/postgres"
    )
    pooler_sess = (
        f"postgresql://postgres.{PROJECT_REF}:{pw_enc}"
        f"@aws-0-{REGION}.pooler.supabase.com:5432/postgres"
    )

    chosen = None
    for label, dsn, host, port in [
        ("direct", direct, f"db.{PROJECT_REF}.supabase.co", 5432),
        ("pooler_session", pooler_sess, f"aws-0-{REGION}.pooler.supabase.com", 5432),
        ("pooler_transaction", pooler_tx, f"aws-0-{REGION}.pooler.supabase.com", 6543),
    ]:
        dns = _dns_ok(host, port)
        print(f"probe {label}: dns={'ok' if dns else 'fail'} host={host}:{port}")
        if not dns:
            continue
        ok, msg = _try_psycopg(dsn)
        print(f"  connect={'ok' if ok else 'fail'} {msg}")
        if ok:
            chosen = (label, dsn)
            break

    if not chosen:
        print("ERR: no working Postgres DSN")
        return 2

    label, dsn = chosen
    text = raw
    text = _set_env_key(text, "USE_SQLITE", "0")
    text = _set_env_key(text, "USE_SUPABASE_DB", "1")
    text = _set_env_key(text, "SUPABASE_URL", SUPABASE_URL)
    text = _set_env_key(text, "SUPABASE_ANON_KEY", ANON_JWT)
    # App often reads SUPABASE_KEY first; use anon until service_role is provided.
    text = _set_env_key(text, "SUPABASE_KEY", ANON_JWT)
    text = _set_env_key(text, "SUPABASE_DB_URL", dsn)
    text = _set_env_key(text, "STORAGE_BACKEND", "supabase")
    text = _set_env_key(text, "SUPABASE_STORAGE_BUCKET", "property-media")
    text = _set_env_key(text, "SUPABASE_BUCKET", "property-media")
    ENV_PATH.write_text(text, encoding="utf-8")
    u = urlparse(dsn)
    print(f"UPDATED .env dsn_mode={label} host={u.hostname} port={u.port} user={u.username}")
    print(f"SUPABASE_URL={SUPABASE_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
