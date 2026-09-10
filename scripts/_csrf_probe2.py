#!/usr/bin/env python3
"""Low-level cookie dump + CSRF validate against production."""
from __future__ import annotations

import json
import re
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE = "https://jakkas-property-website.vercel.app"


def main() -> None:
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    resp = opener.open(Request(BASE + "/contact", headers={"User-Agent": "diag"}), timeout=45)
    html = resp.read().decode("utf-8", "replace")
    print("contact_status", getattr(resp, "status", None))
    for c in jar:
        print(
            "cookie",
            c.name,
            "secure=",
            c.secure,
            "rest=",
            getattr(c, "_rest", {}),
            "value_len=",
            len(c.value or ""),
        )
    meta = re.search(
        r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    )
    hidden = re.search(
        r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    )
    tok_meta = meta.group(1) if meta else None
    tok_form = hidden.group(1) if hidden else None
    print("meta_token", bool(tok_meta), "form_token", bool(tok_form), "same", tok_meta == tok_form)
    tok = tok_form or tok_meta
    body = json.dumps(
        {
            "name": "Cloud Verify Lead",
            "mobile": "9876501234",
            "email": "cloud.verify@example.com",
            "message": "csrf-probe-2",
            "source": "diag",
        }
    ).encode()
    req = Request(
        BASE + "/api/inquiry",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "diag",
            "X-CSRFToken": tok or "",
            "Referer": BASE + "/contact",
            "Origin": BASE,
        },
    )
    try:
        r = opener.open(req, timeout=45)
        print("post", r.status, r.read()[:400])
    except HTTPError as e:
        print("post", e.code, e.read()[:400])

    # Form-encoded fallback (how Flask-WTF traditionally validates)
    from urllib.parse import urlencode

    form = urlencode(
        {
            "csrf_token": tok or "",
            "name": "Cloud Verify Lead",
            "mobile": "9876501234",
            "email": "cloud.verify@example.com",
            "message": "csrf-probe-form",
            "source": "diag",
        }
    ).encode()
    req2 = Request(
        BASE + "/api/inquiry",
        data=form,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "diag",
            "Referer": BASE + "/contact",
        },
    )
    try:
        r2 = opener.open(req2, timeout=45)
        print("form_post", r2.status, r2.read()[:400])
    except HTTPError as e:
        print("form_post", e.code, e.read()[:400])


if __name__ == "__main__":
    main()
