from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "preview"
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("home", "http://127.0.0.1:5000/"),
    ("properties", "http://127.0.0.1:5000/properties"),
    ("about", "http://127.0.0.1:5000/about"),
    ("services", "http://127.0.0.1:5000/services"),
    ("chatbot", "http://127.0.0.1:5000/chatbot"),
    ("contact", "http://127.0.0.1:5000/contact"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    for name, url in PAGES:
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1800)
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
        print(f"captured {name}")
    browser.close()
