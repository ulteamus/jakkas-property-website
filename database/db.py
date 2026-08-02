import os
import logging
import sqlite3
import mysql.connector
from mysql.connector import Error
from flask import g, current_app

_using_sqlite = None
logger = logging.getLogger(__name__)


def use_sqlite():
    global _using_sqlite
    if _using_sqlite is not None:
        return _using_sqlite
    env = os.getenv("USE_SQLITE", "0").strip().lower()
    if env in ("1", "true", "yes"):
        _using_sqlite = True
        return True
    if os.getenv("VERCEL") and env in ("auto", ""):
        _using_sqlite = True
        return True
    if env in ("0", "false", "no"):
        _using_sqlite = False
        return False
    if env not in ("auto", ""):
        raise RuntimeError("Invalid USE_SQLITE value. Use 1/true, 0/false, or auto.")

    # Explicit auto mode: try MySQL, then controlled SQLite fallback.
    try:
        cfg = _mysql_config()
        conn = mysql.connector.connect(**cfg)
        conn.close()
        _using_sqlite = False
    except Error as exc:
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
    if not use_sqlite():
        return sql
    from database.sqlite_init import adapt_sql
    return adapt_sql(sql)


def get_connection():
    if use_sqlite():
        if "db_conn" not in g:
            from database.sqlite_init import init_db, DB_PATH
            init_db()
            conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            g.db_conn = conn
        return g.db_conn
    if "db_conn" not in g:
        try:
            g.db_conn = mysql.connector.connect(**_mysql_config())
        except Error as exc:
            if os.getenv("FLASK_ENV", "").strip().lower() == "production":
                raise
            global _using_sqlite
            logger.warning(
                "MySQL unavailable at runtime; falling back to SQLite for local development."
            )
            _using_sqlite = True
            from database.sqlite_init import init_db, DB_PATH
            init_db()
            conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            g.db_conn = conn
    return g.db_conn


def close_connection(_exc=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        if use_sqlite():
            conn.close()
        elif conn.is_connected():
            conn.close()


def _rows_to_dict(rows):
    if not rows:
        return rows
    if use_sqlite():
        return [dict(r) for r in rows]
    return rows


def query_all(sql, params=None):
    sql = _adapt_sql(sql)
    conn = get_connection()
    if use_sqlite():
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
    sql = _adapt_sql(sql)
    conn = get_connection()
    if use_sqlite():
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


def execute_many(sql, params_list):
    sql = _adapt_sql(sql)
    conn = get_connection()
    if use_sqlite():
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
        if use_sqlite():
            from database.sqlite_init import init_db
            init_db()
            return True
        conn = mysql.connector.connect(**_mysql_config())
        ok = conn.is_connected()
        conn.close()
        return ok
    except Error:
        return False
