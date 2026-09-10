#!/usr/bin/env python3
"""CSRF probe against production (shared cookie jar)."""
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
    html = opener.open(
        Request(BASE + "/", headers={"User-Agent": "diag"}), timeout=45
    ).read().decode("utf-8", "replace")
    m = re.search(
        r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
        html,
        flags=re.I,
    )
    tok = m.group(1) if m else None
    print("csrf", bool(tok), "cookies", [c.name for c in jar])
    body = json.dumps(
        {
            "name": "T",
            "mobile": "9876501234",
            "email": "t@example.com",
            "message": "csrf-probe",
            "source": "diag",
        }
    ).encode()
    for hname in ("X-CSRFToken", "X-CSRF-Token"):
        req = Request(
            BASE + "/api/inquiry",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "diag",
                hname: tok or "",
            },
        )
        try:
            r = opener.open(req, timeout=45)
            print(hname, r.status, r.read()[:300])
        except HTTPError as e:
            print(hname, e.code, e.read()[:300])


if __name__ == "__main__":
    main()
