"""Download luxury property photos and assign them randomly to every listing."""
import random
import shutil
import sys
import uuid
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from database import execute
from models import property as prop_model

# Curated Unsplash luxury / premium real-estate photos
LUXURY_PHOTO_URLS = [
    "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=1280&q=80",
    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1280&q=80",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1280&q=80",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1280&q=80",
    "https://images.unsplash.com/photo-1613490493576-7fde62acd811?w=1280&q=80",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=1280&q=80",
    "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=1280&q=80",
    "https://images.unsplash.com/photo-1523217582562-09f0bc75619a?w=1280&q=80",
    "https://images.unsplash.com/photo-1502672266-47c22eaea43e?w=1280&q=80",
    "https://images.unsplash.com/photo-1522771739534-24471fcdba83?w=1280&q=80",
    "https://images.unsplash.com/photo-1556911223-bff031c9fb7a?w=1280&q=80",
    "https://images.unsplash.com/photo-1480074568708-e7b720bb3f09?w=1280&q=80",
    "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1280&q=80",
    "https://images.unsplash.com/photo-1600047509807-ba389f0a9037?w=1280&q=80",
    "https://images.unsplash.com/photo-1600585154526-990dced4db0d?w=1280&q=80",
    "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1280&q=80",
    "https://images.unsplash.com/photo-1605276374104-dee2a0ed2438?w=1280&q=80",
    "https://images.unsplash.com/photo-1600607687644-c7171b42498f?w=1280&q=80",
]

POOL_DIR = BASE_DIR / "static" / "img" / "luxury-pool"


def _ensure_pool():
    POOL_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for idx, url in enumerate(LUXURY_PHOTO_URLS):
        name = f"luxury-{idx + 1:02d}.jpg"
        path = POOL_DIR / name
        if not path.exists() or path.stat().st_size < 1000:
            try:
                print(f"Downloading {name}...")
                req = urllib.request.Request(url, headers={"User-Agent": "JAKKASH-Property-Bot/1.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    path.write_bytes(resp.read())
            except Exception as exc:
                print(f"Skip {name}: {exc}")
                if path.exists() and path.stat().st_size < 1000:
                    path.unlink(missing_ok=True)
                continue
        if path.exists() and path.stat().st_size >= 1000:
            files.append(path)
    if len(files) < 4:
        raise RuntimeError("Could not download enough luxury photos. Check network and retry.")
    return files


def _clear_property_images(property_id):
    execute("DELETE FROM property_images WHERE property_id=%s", (property_id,))
    execute("UPDATE properties SET primary_image=NULL WHERE id=%s", (property_id,))


def _assign_random_photos(property_id, pool_files, min_photos=4, max_photos=6):
    folder = BASE_DIR / "uploads" / "properties" / str(property_id) / "images"
    folder.mkdir(parents=True, exist_ok=True)

    count = random.randint(min_photos, min(max_photos, len(pool_files)))
    chosen = random.sample(pool_files, k=count)
    primary_rel = None

    for sort_order, src in enumerate(chosen):
        name = f"{uuid.uuid4().hex[:12]}.jpg"
        dest = folder / name
        shutil.copy2(src, dest)
        rel = f"properties/{property_id}/images/{name}"
        prop_model.add_image(property_id, rel, is_primary=(sort_order == 0), sort_order=sort_order)
        if sort_order == 0:
            primary_rel = rel

    return primary_rel, count


def seed_luxury_photos():
    random.seed()
    app = create_app()
    with app.app_context():
        pool = _ensure_pool()
        props = prop_model.search(limit=500, status="available")
        if not props:
            print("No properties found.")
            return

        for prop in props:
            _clear_property_images(prop["id"])
            primary, count = _assign_random_photos(prop["id"], pool)
            print(f"#{prop['id']} {prop['property_name']}: {count} luxury photos (primary: {primary})")

        print(f"Done. Added random luxury photos to {len(props)} properties.")


if __name__ == "__main__":
    seed_luxury_photos()
