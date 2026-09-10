import logging

from database import execute, query_all, query_one
from database.db import skip_runtime_ddl, use_sqlite

logger = logging.getLogger(__name__)


def _runtime_is_sqlite() -> bool:
    """True when the live connection is SQLite (including MySQL/Postgres fallback)."""
    try:
        from flask import g
        from database.db import get_connection

        get_connection()
        if g.get("db_backend") == "sqlite":
            return True
    except Exception:
        pass
    return use_sqlite()


def _ensure_tables():
    """Create testimonials + review_comments if missing. Never drop or truncate."""
    # Resolve backend first so USE_SQLITE=0 + MySQL-down still uses SQLite DDL.
    sqlite_mode = _runtime_is_sqlite()
    if skip_runtime_ddl() and not sqlite_mode:
        return
    if sqlite_mode:
        execute(
            """CREATE TABLE IF NOT EXISTS testimonials (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               client_name TEXT NOT NULL,
               client_location TEXT DEFAULT 'Surat',
               review_text TEXT NOT NULL,
               rating INTEGER DEFAULT 5,
               is_active INTEGER DEFAULT 1,
               created_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        execute(
            """CREATE TABLE IF NOT EXISTS review_comments (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               testimonial_id INTEGER NOT NULL,
               commenter_name TEXT NOT NULL,
               commenter_email TEXT,
               comment_text TEXT NOT NULL,
               is_active INTEGER DEFAULT 1,
               admin_id INTEGER,
               created_at TEXT DEFAULT (datetime('now')),
               FOREIGN KEY (testimonial_id) REFERENCES testimonials(id)
            )"""
        )
        # Product alias so SELECT FROM reviews works locally like Supabase.
        try:
            execute(
                """CREATE VIEW IF NOT EXISTS reviews AS
                   SELECT id, client_name, client_location, review_text,
                          rating, is_active, created_at
                   FROM testimonials"""
            )
        except Exception as exc:
            logger.warning("Could not create local reviews view: %s", exc)
        return

    execute(
        """CREATE TABLE IF NOT EXISTS testimonials (
           id INT AUTO_INCREMENT PRIMARY KEY,
           client_name VARCHAR(120) NOT NULL,
           client_location VARCHAR(120) DEFAULT 'Surat',
           review_text TEXT NOT NULL,
           rating TINYINT DEFAULT 5,
           is_active TINYINT(1) DEFAULT 1,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    execute(
        """CREATE TABLE IF NOT EXISTS review_comments (
           id INT AUTO_INCREMENT PRIMARY KEY,
           testimonial_id INT NOT NULL,
           commenter_name VARCHAR(140) NOT NULL,
           commenter_email VARCHAR(180),
           comment_text TEXT NOT NULL,
           is_active TINYINT(1) DEFAULT 1,
           admin_id INT NULL,
           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
           INDEX idx_review_comments_testimonial (testimonial_id),
           FOREIGN KEY (testimonial_id) REFERENCES testimonials(id)
        )"""
    )


def _comments_map(review_ids, include_inactive=False):
    if not review_ids:
        return {}
    placeholders = ",".join(["%s"] * len(review_ids))
    sql = (
        "SELECT * FROM review_comments "
        f"WHERE testimonial_id IN ({placeholders})"
    )
    params = list(review_ids)
    if not include_inactive:
        sql += " AND is_active=1"
    sql += " ORDER BY created_at ASC"
    rows = query_all(sql, params)

    mapping = {}
    for row in rows:
        mapping.setdefault(row["testimonial_id"], []).append(row)
    return mapping


def list_reviews(include_inactive=False, limit=100):
    """Fetch active reviews from `testimonials` (or `reviews` view/alias)."""
    try:
        _ensure_tables()
    except Exception as exc:
        logger.exception("reviews._ensure_tables failed: %s", exc)
        return []

    params = [limit]
    # SQLite stores 0/1; Postgres may use boolean — accept both active forms.
    if include_inactive:
        where = ""
    elif _runtime_is_sqlite():
        where = " WHERE is_active=1 OR is_active=TRUE"
    else:
        where = " WHERE is_active IS TRUE OR is_active=1"

    rows = []
    source = None
    # Prefer base table first (always present); then product view `reviews`.
    for table in ("testimonials", "reviews"):
        try:
            rows = query_all(
                f"SELECT * FROM {table}{where} ORDER BY created_at DESC LIMIT %s",
                params,
            ) or []
            source = table
            break
        except Exception as exc:
            logger.warning("Review query failed on table=%s: %s", table, exc)
            rows = []

    # Normalize keys so templates always have client_name / review_text / rating.
    normalized = []
    for row in rows:
        item = dict(row)
        item["client_name"] = (
            item.get("client_name")
            or item.get("name")
            or item.get("reviewer_name")
            or "Anonymous"
        )
        item["client_location"] = (
            item.get("client_location") or item.get("location") or "Surat"
        )
        item["review_text"] = (
            item.get("review_text")
            or item.get("comment")
            or item.get("text")
            or item.get("body")
            or ""
        )
        try:
            item["rating"] = max(1, min(5, int(item.get("rating") or 5)))
        except (TypeError, ValueError):
            item["rating"] = 5
        normalized.append(item)

    review_ids = [row["id"] for row in normalized if row.get("id") is not None]
    try:
        comments = _comments_map(review_ids, include_inactive=include_inactive)
    except Exception as exc:
        logger.warning("review comments load failed: %s", exc)
        comments = {}
    for row in normalized:
        row["comments"] = comments.get(row.get("id"), [])

    logger.info(
        "list_reviews: fetched %s row(s) from %s (include_inactive=%s)",
        len(normalized),
        source or "none",
        include_inactive,
    )
    print(f"[reviews] fetched {len(normalized)} review(s) from {source or 'none'}", flush=True)
    return normalized


def get_review(review_id):
    _ensure_tables()
    return query_one("SELECT * FROM testimonials WHERE id=%s", (review_id,))


def _active_param(is_active) -> bool | int:
    from database.db import use_postgres

    return bool(is_active) if use_postgres() else (1 if is_active else 0)


def create_review(name, location, text, rating=5, is_active=True):
    _ensure_tables()
    final_rating = max(1, min(5, int(rating or 5)))
    return execute(
        """INSERT INTO testimonials (client_name, client_location, review_text, rating, is_active)
           VALUES (%s,%s,%s,%s,%s)""",
        (
            (name or "Anonymous").strip()[:120],
            (location or "Surat").strip()[:120],
            (text or "").strip(),
            final_rating,
            _active_param(is_active),
        ),
    )


def update_review(review_id, name, location, text, rating, is_active=None):
    _ensure_tables()
    final_rating = max(1, min(5, int(rating or 5)))
    if is_active is None:
        execute(
            """UPDATE testimonials
               SET client_name=%s, client_location=%s, review_text=%s, rating=%s
               WHERE id=%s""",
            (
                (name or "Anonymous").strip()[:120],
                (location or "Surat").strip()[:120],
                (text or "").strip(),
                final_rating,
                review_id,
            ),
        )
        return
    execute(
        """UPDATE testimonials
           SET client_name=%s, client_location=%s, review_text=%s, rating=%s, is_active=%s
           WHERE id=%s""",
        (
            (name or "Anonymous").strip()[:120],
            (location or "Surat").strip()[:120],
            (text or "").strip(),
            final_rating,
            _active_param(is_active),
            review_id,
        ),
    )


def delete_review(review_id):
    """Explicit admin delete only — removes review and its comments."""
    _ensure_tables()
    execute("DELETE FROM review_comments WHERE testimonial_id=%s", (review_id,))
    execute("DELETE FROM testimonials WHERE id=%s", (review_id,))


def set_review_active(review_id, is_active):
    _ensure_tables()
    execute(
        "UPDATE testimonials SET is_active=%s WHERE id=%s",
        (_active_param(is_active), review_id),
    )


def create_comment(review_id, commenter_name, comment_text, commenter_email=None, is_active=True, admin_id=None):
    _ensure_tables()
    return execute(
        """INSERT INTO review_comments
           (testimonial_id, commenter_name, commenter_email, comment_text, is_active, admin_id)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (
            review_id,
            (commenter_name or "Visitor").strip()[:140],
            (commenter_email or "").strip()[:180] or None,
            (comment_text or "").strip(),
            _active_param(is_active),
            admin_id,
        ),
    )


def delete_comment(comment_id):
    _ensure_tables()
    execute("DELETE FROM review_comments WHERE id=%s", (comment_id,))
