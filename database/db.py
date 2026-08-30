import os
import logging
import sqlite3
from flask import g, current_app

_using_sqlite = None
_last_db_error = None
logger = logging.getLogger(__name__)


class DatabaseUnavailableError(RuntimeError):
    """Re-exported / local alias for graceful route handling."""


def _mysql_connector():
    """Lazy import — omitted from Vercel serverless bundle (Supabase-only)."""
    import mysql.connector
    from mysql.connector import Error as MySQLError

    return mysql.connector, MySQLError


def last_db_error():
    return _last_db_error


def _set_last_db_error(msg):
    global _last_db_error
    _last_db_error = msg


def use_postgres():
    """True when SUPABASE_DB_URL is set and SQLite is not forced on."""
    try:
        from database.supabase_client import postgres_configured

        return postgres_configured()
    except Exception:
        return False


def skip_runtime_ddl():
    """Postgres schema is applied via database/supabase_schema.sql — skip ALTER/CREATE probes."""
    return use_postgres()


def use_sqlite():
    global _using_sqlite
    if use_postgres():
        return False
    if _using_sqlite is not None:
        return _using_sqlite
    env = os.getenv("USE_SQLITE", "0").strip().lower()
    # Vercel with invalid/placeholder USE_SQLITE from env pull → treat as auto
    if env in {"[sensitive]", "sensitive"}:
        env = "auto" if os.getenv("VERCEL") else "0"
    if env in ("1", "true", "yes"):
        _using_sqlite = True
        return True
    if os.getenv("VERCEL") and env in ("auto", ""):
        _using_sqlite = True
        return True
    # On Vercel, unreachable cloud Postgres config → SQLite so pages still render
    if os.getenv("VERCEL") and env in ("0", "false", "no"):
        if not use_postgres():
            logger.warning(
                "Postgres unavailable on Vercel; falling back to ephemeral SQLite."
            )
            _using_sqlite = True
            return True
    if env in ("0", "false", "no"):
        _using_sqlite = False
        return False
    if env not in ("auto", ""):
        raise RuntimeError("Invalid USE_SQLITE value. Use 1/true, 0/false, or auto.")

    # Explicit auto mode: try MySQL, then controlled SQLite fallback.
    try:
        mysql, MySQLError = _mysql_connector()
        cfg = _mysql_config()
        conn = mysql.connect(**cfg)
        conn.close()
        _using_sqlite = False
    except Exception as exc:
        if os.getenv("FLASK_ENV", "").strip().lower() == "production":
            raise RuntimeError(
                "MySQL is unavailable and production fallback to SQLite is blocked. "
                "Fix MySQL connectivity or set USE_SQLITE=1 only for controlled local usage."
            ) from exc
        logger.warning(
            "MySQL unavailable; falling back to SQLite because USE_SQLITE=auto is enabled."
        )
        _using_sqlite = True
    return _using_sqlite


def _mysql_config():
    return {
        "host": current_app.config["MYSQL_HOST"],
        "port": current_app.config["MYSQL_PORT"],
        "user": current_app.config["MYSQL_USER"],
        "password": current_app.config["MYSQL_PASSWORD"],
        "database": current_app.config["MYSQL_DATABASE"],
    }


def _adapt_sql(sql):
    if use_postgres():
        from database.supabase_client import adapt_sql_postgres

        return adapt_sql_postgres(sql)
    if not use_sqlite():
        return sql
    from database.sqlite_init import adapt_sql
    return adapt_sql(sql)


def _force_sqlite_fallback(reason: str):
    global _using_sqlite
    _using_sqlite = True
    _set_last_db_error(reason)
    logger.warning("Falling back to SQLite: %s", reason)
    if "db_conn" in g:
        try:
            close_connection()
        except Exception:
            g.pop("db_conn", None)
            g.pop("db_backend", None)


def get_connection():
    if use_postgres():
        # Pool borrow — must be returned via close_connection / putconn
        if "db_conn" not in g or g.get("db_backend") != "postgres":
            from database.supabase_client import (
                DatabaseUnavailableError as PgUnavailable,
                get_pg_connection,
            )

            try:
                g.db_conn = get_pg_connection()
                g.db_backend = "postgres"
            except PgUnavailable as exc:
                if os.getenv("VERCEL"):
                    _force_sqlite_fallback(str(exc))
                else:
                    _set_last_db_error(str(exc))
                    raise DatabaseUnavailableError(str(exc)) from exc
        if g.get("db_backend") == "postgres":
            return g.db_conn
    if use_sqlite():
        if "db_conn" not in g or g.get("db_backend") != "sqlite":
            from database.sqlite_init import init_db, DB_PATH
            init_db()
            conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
            except Exception:
                pass
            g.db_conn = conn
            g.db_backend = "sqlite"
        return g.db_conn
    if "db_conn" not in g:
        try:
            mysql, _ = _mysql_connector()
            g.db_conn = mysql.connect(**_mysql_config())
            g.db_backend = "mysql"
        except Exception as exc:
            if os.getenv("FLASK_ENV", "").strip().lower() == "production" and not os.getenv("VERCEL"):
                raise
            global _using_sqlite
            logger.warning(
                "MySQL unavailable at runtime; falling back to SQLite for local development."
            )
            _using_sqlite = True
            from database.sqlite_init import init_db, DB_PATH
            init_db()
            conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
            except Exception:
                pass
            g.db_conn = conn
            g.db_backend = "sqlite"
    return g.db_conn


def close_connection(_exc=None):
    conn = g.pop("db_conn", None)
    backend = g.pop("db_backend", None)
    if conn is None:
        return
    if backend == "postgres":
        from database.supabase_client import put_pg_connection

        # force=True: end of request — return the request-scoped conn to the pool
        put_pg_connection(conn, force=True)
        return
    if use_sqlite() or backend == "sqlite":
        conn.close()
    elif hasattr(conn, "is_connected") and conn.is_connected():
        conn.close()


def _rows_to_dict(rows):
    if not rows:
        return rows
    if use_sqlite():
        return [dict(r) for r in rows]
    return rows


def query_all(sql, params=None):
    if use_postgres():
        from database.supabase_client import (
            DatabaseUnavailableError as PgUnavailable,
            pg_query_all,
        )

        try:
            return pg_query_all(sql, params)
        except PgUnavailable as exc:
            if os.getenv("VERCEL"):
                _force_sqlite_fallback(str(exc))
            else:
                _set_last_db_error(str(exc))
                raise DatabaseUnavailableError(str(exc)) from exc
    sql = _adapt_sql(sql)
    try:
        conn = get_connection()
    except DatabaseUnavailableError:
        raise
    if use_sqlite() or g.get("db_backend") == "sqlite":
        cur = conn.cursor()
        cur.execute(sql, params or ())
        return _rows_to_dict(cur.fetchall())
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    rows = cursor.fetchall()
    cursor.close()
    return rows


def query_one(sql, params=None):
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    if use_postgres():
        from database.supabase_client import (
            DatabaseUnavailableError as PgUnavailable,
            pg_execute,
        )

        try:
            return pg_execute(sql, params)
        except PgUnavailable as exc:
            if os.getenv("VERCEL"):
                _force_sqlite_fallback(str(exc))
            else:
                _set_last_db_error(str(exc))
                raise DatabaseUnavailableError(str(exc)) from exc
    sql = _adapt_sql(sql)
    last_exc = None
    for attempt in range(4):
        try:
            conn = get_connection()
            if use_sqlite() or g.get("db_backend") == "sqlite":
                cur = conn.cursor()
                cur.execute(sql, params or ())
                conn.commit()
                return cur.lastrowid
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            conn.commit()
            last_id = cursor.lastrowid
            cursor.close()
            return last_id
        except Exception as exc:
            last_exc = exc
            msg = str(exc).lower()
            if "locked" in msg or "busy" in msg:
                import time

                time.sleep(0.02 * (attempt + 1))
                continue
            raise
    raise last_exc


def execute_many(sql, params_list):
    if use_postgres():
        from database.supabase_client import (
            DatabaseUnavailableError as PgUnavailable,
            pg_execute_many,
        )

        try:
            return pg_execute_many(sql, params_list)
        except PgUnavailable as exc:
            if os.getenv("VERCEL"):
                _force_sqlite_fallback(str(exc))
            else:
                _set_last_db_error(str(exc))
                raise DatabaseUnavailableError(str(exc)) from exc
    sql = _adapt_sql(sql)
    conn = get_connection()
    if use_sqlite() or g.get("db_backend") == "sqlite":
        cur = conn.cursor()
        cur.executemany(sql, params_list)
        conn.commit()
        return
    cursor = conn.cursor()
    cursor.executemany(sql, params_list)
    conn.commit()
    cursor.close()


def test_connection():
    try:
        if use_postgres():
            row = query_one("SELECT 1 AS ok")
            return bool(row and row.get("ok") == 1)
        if use_sqlite():
            from database.sqlite_init import init_db
            init_db()
            return True
        mysql, _ = _mysql_connector()
        conn = mysql.connect(**_mysql_config())
        ok = conn.is_connected()
        conn.close()
        return ok
    except Exception as exc:
        _set_last_db_error(str(exc))
        return False
