"""Production readiness route audit."""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app

app = create_app()
client = app.test_client()

PUBLIC_ROUTES = [
    "/",
    "/properties",
    "/chatbot",
    "/about",
    "/contact",
    "/testimonials",
    "/sell-property",
    "/price-ai",
]

ADMIN_ROUTES = [
    "/admin/",
    "/admin/properties",
    "/admin/inquiries",
    "/admin/sell-properties",
    "/admin/employees",
    "/admin/settings",
    "/admin/activity",
    "/admin/visits",
    "/admin/login",
]

errors = []
warnings = []
ok = []


def check(name, resp, allow_redirect=False):
    code = resp.status_code
    if code == 500:
        errors.append(f"{name}: 500 - {resp.data[:500]}")
    elif code in (301, 302, 303, 307, 308) and allow_redirect:
        ok.append(f"{name}: {code} redirect -> {resp.headers.get('Location', '?')}")
    elif code == 200:
        ok.append(f"{name}: 200")
    elif code == 404 and "property" in name:
        warnings.append(f"{name}: 404 (no property)")
    elif code in (301, 302, 303, 307, 308):
        ok.append(f"{name}: {code} redirect -> {resp.headers.get('Location', '?')}")
    else:
        errors.append(f"{name}: {code} - {resp.data[:300]}")


print("=== PUBLIC ROUTES ===")
for route in PUBLIC_ROUTES:
    try:
        resp = client.get(route, follow_redirects=False)
        check(route, resp, allow_redirect=(route == "/price-ai"))
    except Exception as e:
        errors.append(f"{route}: EXCEPTION {e}")
        traceback.print_exc()

print("=== PROPERTY DETAILS ===")
with app.app_context():
    from models import property as prop_model
    props = prop_model.list_all(limit=5) if hasattr(prop_model, "list_all") else []
    if not props:
        try:
            from database import query_all
            props = query_all("SELECT slug FROM properties WHERE status='available' LIMIT 5")
        except Exception:
            props = []

slugs = []
for p in props:
    slug = p.get("slug") if isinstance(p, dict) else None
    if slug:
        slugs.append(slug)

if not slugs:
    warnings.append("No property slugs found for detail page test")

for slug in slugs[:3]:
    route = f"/property/{slug}"
    try:
        resp = client.get(route)
        check(route, resp)
    except Exception as e:
        errors.append(f"{route}: EXCEPTION {e}")

print("=== ADMIN LOGIN ===")
try:
    login_resp = client.post(
        "/admin/login",
        data={"username": "sam", "password": "jodika"},
        follow_redirects=False,
    )
    check("POST /admin/login (sam/jodika)", login_resp, allow_redirect=True)
except Exception as e:
    errors.append(f"Admin login: EXCEPTION {e}")

print("=== ADMIN ROUTES (authenticated) ===")
for route in ADMIN_ROUTES:
    try:
        resp = client.get(route, follow_redirects=False)
        check(route, resp, allow_redirect=(route == "/admin/login"))
    except Exception as e:
        errors.append(f"{route}: EXCEPTION {e}")

print("=== API SMOKE ===")
try:
    csrf = None
    with client.session_transaction() as sess:
        pass
    # Get CSRF from a page
    page = client.get("/chatbot")
    import re
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.data.decode("utf-8", errors="replace"))
    if not m:
        m = re.search(r'"csrf_token"\s*:\s*"([^"]+)"', page.data.decode("utf-8", errors="replace"))
    csrf = m.group(1) if m else None

    if csrf:
        chat_resp = client.post(
            "/api/chat",
            json={"message": "hello"},
            headers={"X-CSRFToken": csrf},
        )
        check("POST /api/chat", chat_resp)
    else:
        warnings.append("Could not extract CSRF token for /api/chat test")

    props_resp = client.get("/api/properties")
    check("GET /api/properties", props_resp)
except Exception as e:
    errors.append(f"API smoke: EXCEPTION {e}")
    traceback.print_exc()

print("\n=== OK ===")
for x in ok:
    print("  ", x)

print("\n=== WARNINGS ===")
for x in warnings:
    print("  ", x)

print("\n=== ERRORS ===")
for x in errors:
    print("  ", x)

sys.exit(1 if errors else 0)
