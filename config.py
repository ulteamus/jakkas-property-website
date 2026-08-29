import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent

# Company
COMPANY_NAME = "JAKKASH PROPERTY CONSULTANCY"
COMPANY_OWNER = "JAKKASH Team"
COMPANY_ADDRESS = os.getenv(
    "COMPANY_ADDRESS",
    "40,Ganesh Krupa Soc,Opp Gail Tower ,Anand Mahal Road ,Surat 395009",
)
COMPANY_PHONE = "+91 85117-51119"
COMPANY_PHONE_RAW = "918511751119"
COMPANY_EMAIL = os.getenv("COMPANY_EMAIL", "Jakkashproperty@gmail.com")
COMPANY_WHATSAPP = os.getenv("COMPANY_WHATSAPP", COMPANY_PHONE_RAW)
COMPANY_LAT = 21.1702
COMPANY_LNG = 72.8311
SURAT_CENTER = {"lat": 21.1702, "lng": 72.8311}

# Uploads
if os.getenv("VERCEL"):
    UPLOAD_ROOT = Path("/tmp/uploads/properties")
else:
    UPLOAD_ROOT = BASE_DIR / "uploads" / "properties"
ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_VIDEO = {"mp4", "mov", "webm"}
ALLOWED_DOC = {"pdf"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# Supabase Storage (preferred for local + Vercel when credentials are set)
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
    or ""
).strip()
SUPABASE_DB_URL = (
    os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or ""
).strip()
SUPABASE_BUCKET = (
    os.getenv("SUPABASE_BUCKET")
    or os.getenv("SUPABASE_STORAGE_BUCKET")
    or "property-media"
).strip()
STORAGE_BACKEND = (os.getenv("STORAGE_BACKEND") or "").strip().lower()
SUPABASE_ENABLED = bool(SUPABASE_URL and SUPABASE_KEY)
SUPABASE_DB_ENABLED = bool(SUPABASE_DB_URL.startswith("postgres")) and (
    (os.getenv("USE_SQLITE") or "0").strip().lower() not in {"1", "true", "yes", "on"}
)

# Cloudinary persistent media (optional secondary backend)
CLOUDINARY_URL = (os.getenv("CLOUDINARY_URL") or "").strip()
CLOUDINARY_CLOUD_NAME = (os.getenv("CLOUDINARY_CLOUD_NAME") or "").strip()
CLOUDINARY_API_KEY = (os.getenv("CLOUDINARY_API_KEY") or "").strip()
CLOUDINARY_API_SECRET = (os.getenv("CLOUDINARY_API_SECRET") or "").strip()
CLOUDINARY_ENABLED = bool(
    CLOUDINARY_URL
    or (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)
)

# ML models
ML_DIR = BASE_DIR / "ml" / "models"
LEAD_MODEL_PATH = ML_DIR / "lead_scorer.pkl"
PRICE_MODEL_PATH = ML_DIR / "price_predictor.pkl"

PROPERTY_TYPES = [
    "apartment",
    "flat",
    "villa",
    "bungalow",
    "plot",
    "commercial",
    "residential",
    "shop",
    "office",
]
PUBLIC_PROPERTY_TYPES = [
    "apartment",
    "flat",
    "villa",
    "bungalow",
    "plot",
    "commercial",
    "residential",
]
LEAD_STATUSES = ["new", "contacted", "interested", "site_visit_scheduled", "closed"]
LEAD_TIERS = ["cold", "warm", "hot"]

MARKER_ICONS = {
    "flat": "flat",
    "shop": "shop",
    "office": "office",
    "bungalow": "bungalow",
    "plot": "plot",
}

_DEV_SECRET_FALLBACK = "jakkash-dev-secret-change-me"


def is_production_runtime() -> bool:
    if os.getenv("VERCEL"):
        return True
    if os.getenv("ENV", "").strip().lower() == "production":
        return True
    return False


def resolve_secret_key() -> str:
    """Return Flask secret key; fail closed in production when unset or default."""
    key = (os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY") or "").strip()
    if not key or key == _DEV_SECRET_FALLBACK:
        if is_production_runtime():
            raise RuntimeError(
                "SECRET_KEY or FLASK_SECRET_KEY must be set in production "
                "(Vercel/ENV=production). The dev fallback secret is not allowed."
            )
        return _DEV_SECRET_FALLBACK
    return key


class Config:
    SECRET_KEY = resolve_secret_key()
    DEBUG = os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "jakkash_property")
    UPLOAD_ROOT = str(UPLOAD_ROOT)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES
    SUPABASE_URL = SUPABASE_URL
    SUPABASE_KEY = SUPABASE_KEY
    SUPABASE_DB_URL = SUPABASE_DB_URL
    SUPABASE_BUCKET = SUPABASE_BUCKET
    SUPABASE_ENABLED = SUPABASE_ENABLED
    SUPABASE_DB_ENABLED = SUPABASE_DB_ENABLED
    STORAGE_BACKEND = STORAGE_BACKEND
    CLOUDINARY_URL = CLOUDINARY_URL
    CLOUDINARY_CLOUD_NAME = CLOUDINARY_CLOUD_NAME
    CLOUDINARY_API_KEY = CLOUDINARY_API_KEY
    CLOUDINARY_API_SECRET = CLOUDINARY_API_SECRET
    CLOUDINARY_ENABLED = CLOUDINARY_ENABLED
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = is_production_runtime() or os.getenv("HTTPS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    PERMANENT_SESSION_LIFETIME = 86400 * 7
    USE_SQLITE = os.getenv("USE_SQLITE", "0").lower()
