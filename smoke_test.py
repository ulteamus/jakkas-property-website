"""
Live / local smoke test for Jakkas Property Website.

Default (safe for remote): seed a few SMOKE_TAG rows, hit key routes,
assert HTTP 200, then delete the tagged rows.

Flags:
  --full-seed   seed 100 properties + 100 reviews (legacy load test; no auto-cleanup)
  --no-seed     skip seeding; only hit routes
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from app import create_app
from database import execute, query_all
from models import property as prop_model
from models import reviews as reviews_model

ROUTES = ("/", "/properties", "/my-listings", "/contact", "/sell-property")
SMOKE_TAG = "SMOKE_TAG_REMOTE"


def _seed_tagged(n_props: int = 3, n_reviews: int = 3) -> dict:
    token = uuid.uuid4().hex[:8]
    tag = f"{SMOKE_TAG}_{token}"
    prop_ids = []
    for i in range(n_props):
        row = prop_model.create(
            {
                "property_name": f"{tag} Prop {i:02d}",
                "property_type": "flat" if i % 2 == 0 else "house",
                "area_name": "Adajan",
                "address": f"{i} {tag} Road, Surat",
                "price": 2_500_000 + i * 1000,
                "bhk": 2,
                "sq_ft": 1000 + i,
                "description": f"{tag} smoke listing",
                "status": "available",
                "listing_type": "sale",
                "listing_intent": "sell",
                "seller_type": "owner",
                "creation_source": "admin",
                "is_featured": False,
            }
        )
        if row and row.get("id"):
            prop_ids.append(row["id"])

    review_ids = []
    for i in range(n_reviews):
        rid = reviews_model.create_review(
            name=f"{tag} Reviewer {i:02d}",
            location="Surat",
            text=f"{tag} review body {i}",
            rating=5,
            is_active=True,
        )
        if rid:
            review_ids.append(rid)
    return {"tag": tag, "prop_ids": prop_ids, "review_ids": review_ids}


def _cleanup_tagged(seed: dict) -> None:
    for pid in seed.get("prop_ids") or []:
        try:
            prop_model.delete(pid)
        except Exception as exc:
            print(f"  warn delete property {pid}: {exc}")
    for rid in seed.get("review_ids") or []:
        try:
            reviews_model.delete_review(rid)
        except Exception as exc:
            print(f"  warn delete review {rid}: {exc}")
    # Belt-and-suspenders by name tag
    tag = seed.get("tag") or SMOKE_TAG
    try:
        execute("DELETE FROM testimonials WHERE client_name LIKE %s", (f"{tag}%",))
    except Exception:
        pass
    try:
        execute("DELETE FROM properties WHERE property_name LIKE %s", (f"{tag}%",))
    except Exception:
        pass


def _seed_full(n: int = 100) -> None:
    token = uuid.uuid4().hex[:8]
    for i in range(n):
        prop_model.create(
            {
                "property_name": f"Smoke Prop {token}-{i:03d}",
                "property_type": "flat",
                "area_name": "Adajan",
                "address": f"{i} Smoke Test Road",
                "price": 2_500_000 + i * 10_000,
                "bhk": 2,
                "sq_ft": 900,
                "description": f"full smoke {token}",
                "status": "available",
                "listing_type": "sale",
                "listing_intent": "sell",
                "seller_type": "owner",
                "creation_source": "admin",
            }
        )
        reviews_model.create_review(
            name=f"Smoke Reviewer {token}-{i:03d}",
            location="Surat",
            text=f"full smoke review {i} {token}",
            rating=(i % 5) + 1,
            is_active=True,
        )


def _time_get(client, path: str, repeats: int = 3) -> dict:
    samples_ms = []
    status = None
    body_len = 0
    has_reviews = False
    for _ in range(repeats):
        t0 = time.perf_counter()
        resp = client.get(path)
        elapsed = (time.perf_counter() - t0) * 1000.0
        samples_ms.append(elapsed)
        status = resp.status_code
        body = resp.get_data(as_text=True) or ""
        body_len = len(body)
        if path == "/":
            has_reviews = ("testimonial-card" in body) or ("jv-testimonial" in body)
    return {
        "path": path,
        "status": status,
        "ok": status == 200,
        "avg_ms": statistics.mean(samples_ms),
        "p50_ms": statistics.median(samples_ms),
        "max_ms": max(samples_ms),
        "body_bytes": body_len,
        "home_has_reviews": has_reviews if path == "/" else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-seed", action="store_true")
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("FLASK_USE_RELOADER", "0")
    os.environ["USE_SQLITE"] = os.getenv("USE_SQLITE", "0")

    from database.supabase_client import reset_clients

    reset_clients()

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    print("=" * 64)
    print("Jakkas smoke_test.py")
    print("=" * 64)

    seed = {"tag": None, "prop_ids": [], "review_ids": []}
    with app.app_context():
        from flask import g
        from database.db import get_connection

        get_connection()
        print("db_backend", g.get("db_backend"))
        if args.full_seed:
            print("Seeding FULL 100/100 (no cleanup)...")
            _seed_full(100)
        elif not args.no_seed:
            print("Seeding tagged rows (3 props + 3 reviews)...")
            seed = _seed_tagged(3, 3)
            print(f"  tag={seed['tag']} props={seed['prop_ids']} reviews={seed['review_ids']}")

    client = app.test_client()
    results = []
    print("\nHitting routes...")
    for path in ROUTES:
        row = _time_get(client, path, repeats=2)
        results.append(row)
        flag = "PASS" if row["ok"] else "FAIL"
        extra = ""
        if path == "/":
            extra = f" reviews_visible={'yes' if row['home_has_reviews'] else 'NO'}"
        print(
            f"  [{flag}] {path:16} status={row['status']} "
            f"avg={row['avg_ms']:.1f}ms max={row['max_ms']:.1f}ms{extra}"
        )

    if seed.get("prop_ids") or seed.get("review_ids"):
        print("\nCleaning tagged smoke rows...")
        with app.app_context():
            _cleanup_tagged(seed)
            left = query_all(
                "SELECT id, property_name FROM properties WHERE property_name LIKE %s LIMIT 5",
                (f"{seed['tag']}%",),
            )
            print(f"  remaining tagged properties={len(left or [])}")

    print("\n" + "=" * 64)
    print("PERFORMANCE REPORT")
    print("=" * 64)
    fails = [r for r in results if not r["ok"]]
    for row in results:
        print(
            f"{row['path']:16} {row['status']:>6} avg={row['avg_ms']:.1f}ms "
            f"p50={row['p50_ms']:.1f}ms max={row['max_ms']:.1f}ms"
        )
    if fails:
        print(f"RESULT: FAIL ({len(fails)} route(s))")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
