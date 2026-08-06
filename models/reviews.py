from database import execute, query_all, query_one
from database.db import use_sqlite


def _ensure_tables():
    """Create testimonials + review_comments if missing. Never drop or truncate."""
    if use_sqlite():
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
    _ensure_tables()
    sql = "SELECT * FROM testimonials"
    params = []
    if not include_inactive:
        sql += " WHERE is_active=1"
    sql += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    rows = query_all(sql, params)
    review_ids = [row["id"] for row in rows]
    comments = _comments_map(review_ids, include_inactive=include_inactive)
    for row in rows:
        row["comments"] = comments.get(row["id"], [])
    return rows


def get_review(review_id):
    _ensure_tables()
    return query_one("SELECT * FROM testimonials WHERE id=%s", (review_id,))


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
            1 if is_active else 0,
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
            1 if is_active else 0,
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
    execute("UPDATE testimonials SET is_active=%s WHERE id=%s", (1 if is_active else 0, review_id))


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
            1 if is_active else 0,
            admin_id,
        ),
    )


def delete_comment(comment_id):
    _ensure_tables()
    execute("DELETE FROM review_comments WHERE id=%s", (comment_id,))
