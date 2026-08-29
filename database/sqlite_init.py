"""SQLite backend for local development when MySQL is unavailable."""
import os
import shutil
import sqlite3
from pathlib import Path

from database.schema import seed_default_admin_if_empty

if os.getenv("VERCEL"):
    DB_PATH = Path("/tmp/jakkash.db")
else:
    DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jakkash.db"


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def adapt_sql(sql):
    """Convert MySQL-style SQL to SQLite."""
    s = sql.replace("%s", "?")
    s = s.replace("NOW() - INTERVAL 24 HOUR", "datetime('now', '-24 hours')")
    s = s.replace("NOW()", "datetime('now')")
    s = s.replace("INSERT IGNORE INTO", "INSERT OR IGNORE INTO")
    if "ON DUPLICATE KEY UPDATE search_count=search_count+1" in s:
        s = s.replace(
            "INSERT INTO area_demand (area_name, search_count) VALUES (?,1)\n               ON DUPLICATE KEY UPDATE search_count=search_count+1",
            "INSERT INTO area_demand (area_name, search_count) VALUES (?, 1) ON CONFLICT(area_name) DO UPDATE SET search_count=search_count+1",
        )
        s = s.replace(
            "INSERT INTO area_demand (area_name, search_count) VALUES (?,1) ON DUPLICATE KEY UPDATE search_count=search_count+1",
            "INSERT INTO area_demand (area_name, search_count) VALUES (?, 1) ON CONFLICT(area_name) DO UPDATE SET search_count=search_count+1",
        )
    return s


def _bootstrap_vercel_db():
    seed_db = Path(__file__).resolve().parent.parent / "api" / "seed" / "jakkash.db"
    if not seed_db.exists():
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        shutil.copy2(seed_db, DB_PATH)


def init_db():
    if os.getenv("VERCEL"):
        _bootstrap_vercel_db()

    conn = _connect()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS admins (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      email TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      full_name TEXT DEFAULT 'Sam',
      role TEXT DEFAULT 'main_admin',
      permissions_json TEXT,
      phone TEXT,
      phone_verified INTEGER DEFAULT 0,
      require_otp INTEGER DEFAULT 1,
      mobile_otp_enabled INTEGER DEFAULT 1,
      mobile_otp_hash TEXT,
      mobile_otp_expires_at TEXT,
      mobile_otp_sent_at TEXT,
      totp_enabled INTEGER DEFAULT 0,
      totp_secret TEXT,
      last_otp_verified_at TEXT,
      created_by_admin_id INTEGER,
      password_reset_failed_attempts INTEGER DEFAULT 0,
      password_reset_locked_until TEXT,
      is_active INTEGER DEFAULT 1,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS properties (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      property_name TEXT NOT NULL,
      slug TEXT UNIQUE,
      property_type TEXT NOT NULL,
      area_name TEXT NOT NULL,
      address TEXT,
      price REAL NOT NULL,
      bhk INTEGER DEFAULT 0,
      sq_ft REAL NOT NULL,
      description TEXT,
      amenities TEXT,
      latitude REAL DEFAULT 21.1702,
      longitude REAL DEFAULT 72.8311,
      status TEXT DEFAULT 'available',
      is_featured INTEGER DEFAULT 0,
      listing_type TEXT DEFAULT 'sale',
      view_count INTEGER DEFAULT 0,
      primary_image TEXT,
      owner_admin_id INTEGER,
      creation_source TEXT DEFAULT 'admin',
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS property_images (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      property_id INTEGER NOT NULL,
      file_path TEXT NOT NULL,
      sort_order INTEGER DEFAULT 0,
      is_primary INTEGER DEFAULT 0,
      uploaded_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS property_videos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      property_id INTEGER NOT NULL,
      file_path TEXT NOT NULL,
      title TEXT,
      sort_order INTEGER DEFAULT 0,
      uploaded_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS property_documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      property_id INTEGER NOT NULL,
      file_path TEXT NOT NULL,
      doc_name TEXT,
      uploaded_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS inquiries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      mobile TEXT NOT NULL,
      email TEXT,
      message TEXT,
      property_id INTEGER,
      source TEXT DEFAULT 'contact_form',
      status TEXT DEFAULT 'new',
      notes TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS owner_submissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      property_id INTEGER,
      owner_name TEXT NOT NULL,
      owner_mobile TEXT NOT NULL,
      owner_alt_mobile TEXT,
      owner_email TEXT,
      owner_address TEXT NOT NULL,
      property_title TEXT NOT NULL,
      property_type TEXT NOT NULL,
      property_status TEXT DEFAULT 'buy',
      bhk INTEGER DEFAULT 0,
      bungalow_number TEXT,
      area_sq_ft REAL,
      price REAL,
      property_address TEXT NOT NULL,
      city TEXT DEFAULT 'Surat',
      location_area TEXT,
      description TEXT,
      amenities_json TEXT,
      listing_intent TEXT DEFAULT 'buy',
      images_json TEXT,
      videos_json TEXT,
      status TEXT DEFAULT 'pending',
      owner_admin_id INTEGER,
      reviewed_by INTEGER,
      reviewed_at TEXT,
      review_note TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS leads (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      mobile TEXT NOT NULL,
      email TEXT,
      budget REAL,
      preferred_area TEXT,
      property_id INTEGER,
      inquiry_id INTEGER,
      status TEXT DEFAULT 'new',
      lead_score INTEGER DEFAULT 0,
      lead_tier TEXT DEFAULT 'cold',
      follow_up_date TEXT,
      is_urgent INTEGER DEFAULT 0,
      whatsapp_clicks INTEGER DEFAULT 0,
      call_clicks INTEGER DEFAULT 0,
      properties_viewed INTEGER DEFAULT 0,
      time_on_site_sec INTEGER DEFAULT 0,
      saved_count INTEGER DEFAULT 0,
      inquiry_date TEXT DEFAULT (datetime('now')),
      last_contacted_at TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS lead_notes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      lead_id INTEGER NOT NULL,
      admin_id INTEGER,
      note TEXT NOT NULL,
      follow_up_date TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS saved_properties (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_id TEXT NOT NULL,
      property_id INTEGER NOT NULL,
      created_at TEXT DEFAULT (datetime('now')),
      UNIQUE(session_id, property_id),
      FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS property_views (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      property_id INTEGER NOT NULL,
      visitor_id TEXT,
      session_id TEXT,
      viewed_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS visitors (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      visitor_id TEXT NOT NULL UNIQUE,
      session_id TEXT,
      ip_hash TEXT,
      user_agent TEXT,
      first_visit TEXT DEFAULT (datetime('now')),
      last_visit TEXT DEFAULT (datetime('now')),
      visit_count INTEGER DEFAULT 1,
      total_time_sec INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS visitor_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      visitor_id TEXT NOT NULL,
      event_type TEXT NOT NULL,
      property_id INTEGER,
      meta TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS search_analytics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      area_name TEXT,
      property_type TEXT,
      min_budget REAL,
      max_budget REAL,
      bhk INTEGER,
      session_id TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS area_demand (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      area_name TEXT NOT NULL UNIQUE,
      view_count INTEGER DEFAULT 0,
      search_count INTEGER DEFAULT 0,
      inquiry_count INTEGER DEFAULT 0,
      demand_score REAL DEFAULT 0,
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS testimonials (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      client_name TEXT NOT NULL,
      client_location TEXT DEFAULT 'Surat',
      review_text TEXT NOT NULL,
      rating INTEGER DEFAULT 5,
      is_active INTEGER DEFAULT 1,
      created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS review_comments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      testimonial_id INTEGER NOT NULL,
      commenter_name TEXT NOT NULL,
      commenter_email TEXT,
      comment_text TEXT NOT NULL,
      is_active INTEGER DEFAULT 1,
      admin_id INTEGER,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (testimonial_id) REFERENCES testimonials(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS seller_profiles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      full_name TEXT NOT NULL,
      mobile TEXT NOT NULL,
      email TEXT,
      address TEXT,
      tags_text TEXT,
      notes TEXT,
      created_by_admin_id INTEGER,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS customer_visits (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      visit_date TEXT NOT NULL,
      client_name TEXT NOT NULL,
      client_address TEXT,
      client_contact TEXT NOT NULL,
      client_requirement TEXT,
      property_id INTEGER,
      executive_admin_id INTEGER,
      executive_name TEXT,
      executive_address TEXT,
      executive_contact TEXT,
      customer_signature_label TEXT,
      executive_signature_label TEXT,
      customer_signature_data TEXT,
      executive_signature_data TEXT,
      created_by_admin_id INTEGER,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS activity_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      admin_id INTEGER,
      action_key TEXT NOT NULL,
      action_label TEXT NOT NULL,
      entity_type TEXT,
      entity_id INTEGER,
      meta_json TEXT,
      created_at TEXT DEFAULT (datetime('now'))
    );
    """)

    if cur.execute("SELECT COUNT(*) FROM properties").fetchone()[0] == 0:
        _seed(cur)

    seed_default_admin_if_empty(cur)

    conn.commit()
    conn.close()


def _seed(cur):
    areas = [
        ("Adajan", 85), ("Vesu", 90), ("Pal", 75), ("Piplod", 88),
        ("Varachha", 70), ("Katargam", 65), ("City Light", 82), ("Althan", 78),
        ("Dumas", 80), ("Hazira", 60), ("Nanachhipwad", 72), ("Ambaji Road", 74),
    ]
    for name, score in areas:
        cur.execute(
            "INSERT OR IGNORE INTO area_demand (area_name, demand_score) VALUES (?, ?)",
            (name, score),
        )

    testimonials = [
        ("Rajesh Patel", "Adajan, Surat", "Jakkash Property helped us find our dream 3BHK. Professional and transparent service.", 5),
        ("Priya Shah", "Vesu, Surat", "Tirth bhai gave honest advice on pricing. Highly recommend for Surat properties.", 5),
        ("Amit Desai", "Piplod, Surat", "Quick site visits and excellent follow-up. Our shop deal closed smoothly.", 5),
    ]
    for name, loc, text, rating in testimonials:
        cur.execute(
            "INSERT INTO testimonials (client_name, client_location, review_text, rating) VALUES (?,?,?,?)",
            (name, loc, text, rating),
        )

    props = [
        ("Premium 3BHK Flat - Vesu", "premium-3bhk-flat-vesu", "flat", "Vesu", "Vesu Main Road, Surat", 8500000, 3, 1450,
         "Spacious 3BHK with modular kitchen and covered parking near VR Mall.", '["parking","lift","security","gym"]', 21.1415, 72.7758, 1),
        ("Commercial Shop - Adajan", "commercial-shop-adajan", "shop", "Adajan", "Adajan Patiya, Surat", 4500000, 0, 450,
         "Prime commercial shop on main road with high footfall.", '["parking","power_backup"]', 21.1956, 72.7934, 1),
        ("Office Space - Piplod", "office-space-piplod", "office", "Piplod", "Piplod, Surat", 120000, 0, 1200,
         "Furnished office in commercial complex.", '["lift","security","cafeteria"]', 21.1608, 72.7712, 0),
        ("Luxury Bungalow - Dumas", "luxury-bungalow-dumas", "bungalow", "Dumas", "Dumas Road, Surat", 25000000, 4, 3500,
         "4BHK bungalow with garden and private terrace.", '["garden","parking","security"]', 21.0892, 72.8145, 1),
        ("Residential Plot - Pal", "residential-plot-pal", "plot", "Pal", "Pal Area, Surat", 3200000, 0, 1800,
         "Clear title plot in developing area.", '["gated","water","electricity"]', 21.2053, 72.8987, 0),
        ("2BHK Flat - Varachha", "2bhk-flat-varachha", "flat", "Varachha", "Varachha Road, Surat", 4200000, 2, 980,
         "Affordable 2BHK near ring road.", '["lift","security"]', 21.2315, 72.8543, 0),
    ]
    for p in props:
        cur.execute(
            """INSERT INTO properties
               (property_name,slug,property_type,area_name,address,price,bhk,sq_ft,description,amenities,latitude,longitude,is_featured)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            p,
        )
