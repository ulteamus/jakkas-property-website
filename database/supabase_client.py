"""
Supabase client singleton + PostgreSQL helpers for Jakkash.

- create_client(SUPABASE_URL, SUPABASE_KEY) for Storage / Auth / PostgREST
- Optional Postgres via SUPABASE_DB_URL (psycopg2) for the existing SQL façade

When credentials are empty, callers must fall back to SQLite/MySQL (see database.db).
"""
from __future__ import annotations

import logging
import os
import re
import threading
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_supabase_client = None
_pg_pool = None
_pg_lock = threading.Lock()
_pg_pool_failed = False
_pg_pool_error: Optional[str] = None
_loopback_warned = False

DEFAULT_STORAGE_BUCKET = "property-media"


class DatabaseUnavailableError(RuntimeError):
    """Raised when Postgres cannot be reached; callers should degrade gracefully."""


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return default


def supabase_url() -> str:
    return _env("SUPABASE_URL").rstrip("/")


def supabase_key() -> str:
    return _env(
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_ANON_KEY",
    )


def supabase_db_url() -> str:
    return _env("SUPABASE_DB_URL", "DATABASE_URL")


def storage_backend() -> str:
    """local | supabase | cloudinary — empty means auto (prefer supabase when configured)."""
    return _env("STORAGE_BACKEND", default="").lower()


def storage_bucket() -> str:
    return _env("SUPABASE_BUCKET", "SUPABASE_STORAGE_BUCKET", default=DEFAULT_STORAGE_BUCKET)


def api_configured() -> bool:
    return bool(supabase_url() and supabase_key())


def _is_loopback_db_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in {"127.0.0.1", "localhost", "::1"}


def postgres_configured() -> bool:
    url = supabase_db_url()
    if not url:
        return False
    # Explicit opt-out while keeping URL for docs/tools
    flag = _env("USE_SUPABASE_DB", "USE_POSTGRES", default="1").lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if _env("USE_SQLITE", default="0").lower() in {"1", "true", "yes", "on"}:
        return False
    if not url.startswith("postgres"):
        return False
    # Vercel cannot reach local Docker Supabase — refuse loopback DSNs
    if os.getenv("VERCEL") and _is_loopback_db_url(url):
        global _loopback_warned
        if not _loopback_warned:
            _loopback_warned = True
            logger.warning(
                "Ignoring loopback SUPABASE_DB_URL on Vercel (%s). "
                "Set a cloud Postgres URL or USE_SQLITE=1.",
                mask_db_url(url),
            )
        return False
    if _pg_pool_failed:
        return False
    return True


def _create_client_compat(url: str, key: str):
    """
    supabase-py 2.10 validates keys as JWTs only.
    New platform keys (sb_secret_ / sb_publishable_) are valid HTTP API keys —
    temporarily relax the JWT regex for those formats.
    """
    from supabase import create_client
    from supabase._sync import client as sync_client

    if not key.startswith(("sb_secret_", "sb_publishable_")):
        return create_client(url, key)

    jwt_pat = r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$"
    _orig_match = sync_client.re.match

    def _match_allow_sb(pattern, string, flags=0):
        if pattern == jwt_pat and isinstance(string, str) and string.startswith(
            ("sb_secret_", "sb_publishable_")
        ):
            return _orig_match(r".+", string)
        return _orig_match(pattern, string, flags)

    sync_client.re.match = _match_allow_sb  # type: ignore[method-assign]
    try:
        return create_client(url, key)
    finally:
        sync_client.re.match = _orig_match  # type: ignore[method-assign]


def get_supabase_client():
    """Lazy singleton Supabase Python client. Raises if credentials missing."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    with _client_lock:
        if _supabase_client is not None:
            return _supabase_client
        if not api_configured():
            raise RuntimeError(
                "Supabase API credentials missing. Set SUPABASE_URL and "
                "SUPABASE_KEY (or SUPABASE_SERVICE_KEY) in .env."
            )
        _supabase_client = _create_client_compat(supabase_url(), supabase_key())
        return _supabase_client


def reset_clients() -> None:
    """Test helper — clear cached client/pool."""
    global _supabase_client, _pg_pool, _pg_pool_failed, _pg_pool_error, _loopback_warned
    with _client_lock:
        _supabase_client = None
    with _pg_lock:
        if _pg_pool is not None:
            try:
                _pg_pool.closeall()
            except Exception:
                pass
        _pg_pool = None
        _pg_pool_failed = False
        _pg_pool_error = None
        _loopback_warned = False


def last_pg_error() -> Optional[str]:
    return _pg_pool_error


def public_storage_url(object_path: str, bucket: Optional[str] = None) -> str:
    bucket = bucket or storage_bucket()
    path = (object_path or "").lstrip("/")
    base = supabase_url()
    if not base:
        return path
    return f"{base}/storage/v1/object/public/{bucket}/{path}"


def adapt_sql_postgres(sql: str) -> str:
    """
    Translate MySQL-flavored SQL used by models into PostgreSQL.

    psycopg2 already uses %s placeholders — leave them alone.
    """
    s = sql
    s = re.sub(r"\bIFNULL\s*\(", "COALESCE(", s, flags=re.IGNORECASE)
    s = s.replace("INSERT IGNORE INTO", "INSERT INTO")
    s = s.replace("INSERT OR IGNORE INTO", "INSERT INTO")
    # Common upsert used by analytics
    if "ON DUPLICATE KEY UPDATE search_count=search_count+1" in s:
        s = s.replace(
            "ON DUPLICATE KEY UPDATE search_count=search_count+1",
            "ON CONFLICT (area_name) DO UPDATE SET search_count = area_demand.search_count + 1",
        )
    # MySQL boolean-ish column comparisons against 0/1
    for col in (
        "is_active",
        "is_featured",
        "phone_verified",
        "require_otp",
        "mobile_otp_enabled",
        "totp_enabled",
        "is_urgent",
        "is_primary",
    ):
        s = re.sub(rf"\b{col}\s*=\s*1\b", f"{col} = TRUE", s, flags=re.IGNORECASE)
        s = re.sub(rf"\b{col}\s*=\s*0\b", f"{col} = FALSE", s, flags=re.IGNORECASE)
    s = re.sub(r"\bTINYINT\(1\)", "BOOLEAN", s, flags=re.IGNORECASE)

    def _mysql_interval(match: re.Match) -> str:
        n = match.group(1)
        unit = match.group(2).lower()
        plural = {
            "hour": "hours",
            "day": "days",
            "minute": "minutes",
            "second": "seconds",
        }.get(unit, unit + "s")
        return f"INTERVAL '{n} {plural}'"

    s = re.sub(
        r"INTERVAL\s+(\d+)\s+(HOUR|DAY|MINUTE|SECOND)\b",
        _mysql_interval,
        s,
        flags=re.IGNORECASE,
    )
    # MySQL SUM(boolean_expr) → Postgres conditional count
    s = re.sub(
        r"SUM\((\w+)='([^']+)'\)",
        r"SUM(CASE WHEN \1='\2' THEN 1 ELSE 0 END)",
        s,
        flags=re.IGNORECASE,
    )
    return s


def _get_pg_pool():
    global _pg_pool, _pg_pool_failed, _pg_pool_error
    if _pg_pool_failed:
        raise DatabaseUnavailableError(
            _pg_pool_error or "PostgreSQL pool previously failed to initialize."
        )
    if _pg_pool is not None:
        return _pg_pool
    with _pg_lock:
        if _pg_pool_failed:
            raise DatabaseUnavailableError(
                _pg_pool_error or "PostgreSQL pool previously failed to initialize."
            )
        if _pg_pool is not None:
            return _pg_pool
        import psycopg2
        import psycopg2.pool

        url = supabase_db_url()
        if not url:
            raise DatabaseUnavailableError("SUPABASE_DB_URL is not configured.")
        if os.getenv("VERCEL") and _is_loopback_db_url(url):
            msg = (
                "SUPABASE_DB_URL points to localhost which is unreachable from Vercel. "
                "Configure a cloud Supabase Postgres URL."
            )
            _pg_pool_failed = True
            _pg_pool_error = msg
            raise DatabaseUnavailableError(msg)
        try:
            # Serverless-safe pool: 1–2 conns per worker, hard connect timeout.
            # connect_timeout / options are passed through to psycopg2.connect().
            max_conn = 2 if os.getenv("VERCEL") else 3
            _pg_pool = psycopg2.pool.ThreadedConnectionPool(
                1,
                max_conn,
                dsn=url,
                connect_timeout=3,
                options="-c statement_timeout=8000",
            )
            return _pg_pool
        except Exception as exc:
            _pg_pool_failed = True
            _pg_pool_error = str(exc)
            logger.error(
                "Failed to create Postgres pool for %s: %s",
                mask_db_url(url),
                exc,
            )
            raise DatabaseUnavailableError(
                f"Cannot connect to PostgreSQL ({mask_db_url(url)}): {exc}"
            ) from exc


def get_pg_connection():
    """Borrow a connection from the pool (caller must putconn).

    Within a Flask app/request context the same connection is reused for the
    whole request so we avoid getconn/putconn/rollback on every query
    (critical when Postgres is cross-region from the serverless worker).
    """
    import time

    try:
        from flask import g, has_app_context

        if has_app_context():
            existing = g.get("db_conn")
            if (
                g.get("db_backend") == "postgres"
                and existing is not None
                and not getattr(existing, "closed", 1)
            ):
                return existing
    except Exception:
        pass

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            pool = _get_pg_pool()
            conn = pool.getconn()
            if getattr(conn, "closed", 0):
                try:
                    pool.putconn(conn, close=True)
                except Exception:
                    pass
                continue
            try:
                from flask import g, has_app_context

                if has_app_context():
                    g.db_conn = conn
                    g.db_backend = "postgres"
            except Exception:
                pass
            return conn
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            last_exc = exc
            # Pool exhaustion is transient — do not permanently kill the pool
            msg = str(exc).lower()
            if "exhausted" in msg or "connection pool" in msg:
                time.sleep(0.05 * (attempt + 1))
                continue
            logger.error("Postgres getconn failed: %s", exc)
            raise DatabaseUnavailableError(f"PostgreSQL connection failed: {exc}") from exc
    raise DatabaseUnavailableError(
        f"PostgreSQL pool exhausted after retries: {last_exc}"
    )


def _return_pg_to_pool(conn) -> None:
    """Actually return a connection to the pool (rollback + putconn)."""
    if conn is None:
        return
    try:
        try:
            if getattr(conn, "status", None) is not None:
                conn.rollback()
        except Exception:
            try:
                _get_pg_pool().putconn(conn, close=True)
                return
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                return
        _get_pg_pool().putconn(conn)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


def put_pg_connection(conn, force: bool = False) -> None:
    """Return a connection to the pool.

    During a Flask request, intermediate puts are no-ops so the request-scoped
    connection stays open. Pass force=True from teardown to release it.
    """
    if conn is None:
        return
    if not force:
        try:
            from flask import g, has_app_context

            if has_app_context() and g.get("db_conn") is conn:
                return
        except Exception:
            pass
    _return_pg_to_pool(conn)


def _pg_retry(op_name: str, fn):
    """Retry once on deadlock / serialization failure, always rollback on error."""
    import time

    last: Exception | None = None
    for attempt in range(2):
        try:
            return fn()
        except DatabaseUnavailableError:
            raise
        except Exception as exc:
            last = exc
            msg = str(exc).lower()
            if attempt == 0 and ("deadlock" in msg or "serialization" in msg or "could not serialize" in msg):
                time.sleep(0.05)
                continue
            logger.error("%s failed: %s", op_name, exc)
            raise DatabaseUnavailableError(f"PostgreSQL {op_name} failed: {exc}") from exc
    raise DatabaseUnavailableError(f"PostgreSQL {op_name} failed: {last}")


def _row_to_dict(cursor, row) -> Optional[dict]:
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def pg_query_all(sql: str, params=None) -> list[dict]:
    sql = adapt_sql_postgres(sql)
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if cur.description is None:
                return []
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except DatabaseUnavailableError:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error("pg_query_all failed: %s", exc)
        raise DatabaseUnavailableError(f"PostgreSQL query failed: {exc}") from exc
    finally:
        put_pg_connection(conn)


def pg_query_one(sql: str, params=None) -> Optional[dict]:
    rows = pg_query_all(sql, params)
    return rows[0] if rows else None


def pg_execute(sql: str, params=None) -> Any:
    sql = adapt_sql_postgres(sql)
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            conn.commit()
            # RETURNING id support if present; else lastval when possible
            if cur.description:
                row = cur.fetchone()
                if row:
                    return row[0]
            try:
                cur.execute("SELECT LASTVAL()")
                val = cur.fetchone()[0]
                return val
            except Exception:
                # Clear aborted-transaction state without undoing committed work
                try:
                    conn.rollback()
                except Exception:
                    pass
                return None
    except DatabaseUnavailableError:
        raise
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error("pg_execute failed: %s", exc)
        raise DatabaseUnavailableError(f"PostgreSQL execute failed: {exc}") from exc
    finally:
        put_pg_connection(conn)


def pg_execute_many(sql: str, params_list) -> None:
    sql = adapt_sql_postgres(sql)
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.executemany(sql, params_list)
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        put_pg_connection(conn)


def mask_db_url(url: str) -> str:
    """Redact password for logs."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            netloc = parsed.netloc.replace(parsed.password, "***")
            return parsed._replace(netloc=netloc).geturl()
    except Exception:
        pass
    return "<redacted>"
