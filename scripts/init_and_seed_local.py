"""Initialize SQLite schema and seed sample Surat listings if empty."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from app import create_app
from database.db import query_one, test_connection, use_sqlite
from database.sqlite_init import DB_PATH, init_db
from models import property as prop_model
from models.admin import Admin


SAMPLES = [
    {
        "property_name": "Vesu Skyline 3BHK Apartment",
        "property_type": "flat",
        "area_name": "Vesu",
        "address": "Near VR Mall, Vesu, Surat",
        "price": 7850000,
        "bhk": 3,
        "sq_ft": 1650,
        "description": "Bright 3BHK with modular kitchen and covered parking. Sample seed listing.",
        "latitude": 21.1415,
        "longitude": 72.7709,
        "status": "available",
        "is_featured": True,
        "listing_type": "sale",
        "primary_image": "/static/uploads/hero-fallback.jpg",
        "creation_source": "admin",
    },
    {
        "property_name": "Adajan Riverside 2BHK Flat",
        "property_type": "apartment",
        "area_name": "Adajan",
        "address": "Palanpur Canal Road, Adajan, Surat",
        "price": 5200000,
        "bhk": 2,
        "sq_ft": 1180,
        "description": "Well-kept 2BHK near schools and riverfront. Sample seed listing.",
        "latitude": 21.1959,
        "longitude": 72.7933,
        "status": "available",
        "is_featured": True,
        "listing_type": "sale",
        "primary_image": "/static/img/default-property.jpg",
        "creation_source": "admin",
    },
    {
        "property_name": "Piplod Corner Commercial Shop",
        "property_type": "shop",
        "area_name": "Piplod",
        "address": "Gaurav Path, Piplod, Surat",
        "price": 9500000,
        "bhk": 0,
        "sq_ft": 620,
        "description": "Ground-floor shop with frontage for retail. Sample seed listing.",
        "latitude": 21.1542,
        "longitude": 72.7835,
        "status": "available",
        "is_featured": False,
        "listing_type": "sale",
        "primary_image": "/static/uploads/hero-fallback.jpg",
        "creation_source": "admin",
        "seller_type": "owner",
    },
    {
        "property_name": "Pal Lakeview 4BHK Bungalow",
        "property_type": "bungalow",
        "area_name": "Pal",
        "address": "Pal Gam Road, Pal, Surat",
        "price": 18500000,
        "bhk": 4,
        "sq_ft": 3200,
        "description": "Independent bungalow with garden parking. Sample seed listing.",
        "latitude": 21.1784,
        "longitude": 72.7578,
        "status": "available",
        "is_featured": True,
        "listing_type": "sale",
        "primary_image": "/static/img/placeholder.jpg",
        "creation_source": "admin",
    },
    {
        "property_name": "Ring Road Office Space",
        "property_type": "office",
        "area_name": "Ring Road",
        "address": "Near Mini Bazar, Ring Road, Surat",
        "price": 45000,
        "bhk": 0,
        "sq_ft": 900,
        "description": "Furnished office on rent near Ring Road. Sample seed listing.",
        "latitude": 21.1850,
        "longitude": 72.8311,
        "status": "available",
        "is_featured": False,
        "listing_type": "rent",
        "listing_intent": "rent",
        "primary_image": "/static/uploads/hero-fallback.jpg",
        "creation_source": "admin",
    },
]


def main():
    app = create_app()
    with app.app_context():
        print(f"USE_SQLITE={use_sqlite()}")
        print(f"DB_PATH={DB_PATH}")
        init_db()
        ok = test_connection()
        print(f"test_connection={ok}")
        Admin.ensure_default()
        count_row = query_one("SELECT COUNT(*) AS c FROM properties")
        before = int((count_row or {}).get("c") or 0)
        print(f"properties_before={before}")
        created = []
        if before == 0:
            for sample in SAMPLES:
                row = prop_model.create(sample)
                created.append(
                    {
                        "id": row.get("id"),
                        "name": row.get("property_name"),
                        "type": row.get("property_type"),
                        "area": row.get("area_name"),
                        "price": row.get("price"),
                        "bhk": row.get("bhk"),
                    }
                )
                print(f"seeded id={row.get('id')} {row.get('property_name')}")
        else:
            print("seed_skipped=tables_not_empty")
        after = int((query_one("SELECT COUNT(*) AS c FROM properties") or {}).get("c") or 0)
        print(f"properties_after={after}")
        print(f"seeded_count={len(created)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
