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

# Cloudinary persistent media (set CLOUDINARY_URL or the three discrete vars on Vercel)
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


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "jakkash-dev-secret-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "jakkash_property")
    UPLOAD_ROOT = str(UPLOAD_ROOT)
    MAX_CONTENT_LENGTH = MAX_UPLOAD_BYTES
    CLOUDINARY_URL = CLOUDINARY_URL
    CLOUDINARY_CLOUD_NAME = CLOUDINARY_CLOUD_NAME
    CLOUDINARY_API_KEY = CLOUDINARY_API_KEY
    CLOUDINARY_API_SECRET = CLOUDINARY_API_SECRET
    CLOUDINARY_ENABLED = CLOUDINARY_ENABLED
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 86400 * 7
    USE_SQLITE = os.getenv("USE_SQLITE", "0").lower()
