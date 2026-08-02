"""Seed sample photos and videos for properties that have none."""
import shutil
import sys
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from models import property as prop_model
HERO_EXTERIOR = BASE_DIR / "static" / "videos" / "hero-exterior.mp4"
HERO_INTERIOR = BASE_DIR / "static" / "videos" / "hero-interior.mp4"

COLORS = [
    ("#f79433", "#1a1a1a"),
    ("#2f6fed", "#ffffff"),
    ("#257d4d", "#ffffff"),
    ("#8d4f10", "#ffffff"),
    ("#5b4b8a", "#ffffff"),
    ("#c0392b", "#ffffff"),
]


def _save_placeholder_image(property_id, title, index, fg, bg):
    folder = BASE_DIR / "uploads" / "properties" / str(property_id) / "images"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}.jpg"
    path = folder / name
    img = Image.new("RGB", (1280, 854), bg)
    draw = ImageDraw.Draw(img)
    text = (title or "JAKKASH Property")[:42]
    draw.text((64, 360), text, fill=fg)
    draw.text((64, 430), f"Photo {index + 1}", fill=fg)
    img.save(path, quality=88)
    return f"properties/{property_id}/images/{name}"


def _copy_video(property_id, source, sort_order):
    if not source.exists():
        return None
    folder = BASE_DIR / "uploads" / "properties" / str(property_id) / "videos"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}{source.suffix.lower()}"
    dest = folder / name
    if not dest.exists():
        shutil.copy2(source, dest)
    rel = f"properties/{property_id}/videos/{name}"
    prop_model.add_video(property_id, rel, title=source.stem.replace("-", " ").title(), sort_order=sort_order)
    return rel


def seed_media():
    app = create_app()
    with app.app_context():
        props = prop_model.search(limit=200, status="available")
        seeded = 0
        for idx, prop in enumerate(props):
            media = prop_model.get_media(prop["id"])
            has_images = bool(media["images"])
            has_videos = bool(media["videos"])
            if has_images and has_videos:
                continue

            if not has_images:
                fg, bg = COLORS[idx % len(COLORS)]
                for i in range(3):
                    rel = _save_placeholder_image(
                        prop["id"],
                        prop.get("property_name"),
                        i,
                        fg,
                        bg,
                    )
                    prop_model.add_image(prop["id"], rel, is_primary=(i == 0), sort_order=i)

            if not has_videos:
                _copy_video(prop["id"], HERO_EXTERIOR, 0)
                _copy_video(prop["id"], HERO_INTERIOR, 1)

            seeded += 1
            print(f"Seeded media for #{prop['id']} {prop['property_name']}")

        print(f"Done. Updated {seeded} properties.")


if __name__ == "__main__":
    seed_media()
