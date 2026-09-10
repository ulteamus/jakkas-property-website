"""Quick storage write test against property-media using SUPABASE_KEY from .env."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
vals = dotenv_values(ROOT / ".env")
URL = (vals.get("SUPABASE_URL") or "").rstrip("/")
KEY = vals.get("SUPABASE_KEY") or vals.get("SUPABASE_SERVICE_KEY") or ""
BUCKET = vals.get("SUPABASE_STORAGE_BUCKET") or vals.get("SUPABASE_BUCKET") or "property-media"


def main() -> int:
    if not URL or not KEY:
        print("missing URL/KEY")
        return 1
    name = f"agent-verify/{uuid.uuid4().hex}.txt"
    body = b"jakkas mumbai service_role storage write ok\n"
    endpoint = f"{URL}/storage/v1/object/{BUCKET}/{name}"
    req = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {KEY}",
            "apikey": KEY,
            "Content-Type": "text/plain",
            "x-upsert": "true",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
    print("upload_status", status)
    print("upload_body_prefix", raw[:160].replace("\n", " "))
    # public read
    pub = f"{URL}/storage/v1/object/public/{BUCKET}/{name}"
    try:
        with urlopen(Request(pub, method="GET"), timeout=20) as resp:
            pub_status = resp.status
            pub_body = resp.read()
    except HTTPError as exc:
        pub_status = exc.code
        pub_body = b""
    print("public_get_status", pub_status, "bytes", len(pub_body))
    ok = status in (200, 201) and pub_status == 200
    print("OVERALL", "PASS" if ok else "FAIL")
    # cleanup best-effort
    try:
        del_req = Request(
            endpoint,
            method="DELETE",
            headers={"Authorization": f"Bearer {KEY}", "apikey": KEY},
        )
        with urlopen(del_req, timeout=20) as resp:
            print("cleanup_status", resp.status)
    except Exception as exc:
        print("cleanup_skip", type(exc).__name__)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
