"""Prepare api/index.py and copy templates/static for Vercel serverless bundle."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "api"


def copy_tree(name: str) -> None:
    src = ROOT / name
    dest = API / name
    if not src.exists():
        return
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def main() -> None:
    API.mkdir(exist_ok=True)
    for folder in ("templates", "static", "ml"):
        copy_tree(folder)

    (API / "index.py").write_text(
        """import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
ROOT = API_DIR.parent
sys.path.insert(0, str(ROOT))
os.environ["VERCEL_ASSET_ROOT"] = str(API_DIR)

from app import create_app

app = create_app()
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
