#!/usr/bin/env python3
"""Patch .env with local Supabase credentials from `supabase status -o env`."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

KEY_MAP = {
    "API_URL": "SUPABASE_URL",
    "SERVICE_ROLE_KEY": "SUPABASE_KEY",
    "ANON_KEY": "SUPABASE_ANON_KEY",
    "DB_URL": "SUPABASE_DB_URL",
}


def parse_status_env(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        out[key] = value
    return out


def patch_env(updates: dict[str, str]) -> None:
    text = ENV_PATH.read_text(encoding="utf-8-sig")
    for key, value in updates.items():
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        replacement = f"{key}={value}"
        if pattern.search(text):
            text = pattern.sub(replacement, text)
        else:
            text = text.rstrip() + f"\n{replacement}\n"
    ENV_PATH.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    scoop = Path.home() / "scoop" / "shims"
    env = dict(__import__("os").environ)
    env["PATH"] = str(scoop) + ";" + env.get("PATH", "")
    proc = subprocess.run(
        ["supabase", "status", "-o", "env"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return proc.returncode
    status = parse_status_env(proc.stdout)
    updates = {
        KEY_MAP["API_URL"]: status.get("API_URL", "http://127.0.0.1:54321"),
        KEY_MAP["SERVICE_ROLE_KEY"]: status.get("SERVICE_ROLE_KEY", ""),
        KEY_MAP["ANON_KEY"]: status.get("ANON_KEY", ""),
        KEY_MAP["DB_URL"]: status.get("DB_URL", ""),
        "SUPABASE_SERVICE_KEY": status.get("SERVICE_ROLE_KEY", ""),
        "SUPABASE_SERVICE_ROLE_KEY": status.get("SERVICE_ROLE_KEY", ""),
        "USE_SQLITE": "0",
        "STORAGE_BACKEND": "supabase",
        "SUPABASE_STORAGE_BUCKET": "property-media",
        "SUPABASE_BUCKET": "property-media",
    }
    patch_env(updates)
    print("Patched .env for local Supabase")
    print(f"SUPABASE_URL={updates['SUPABASE_URL']}")
    print(f"SUPABASE_DB_URL={updates['SUPABASE_DB_URL']}")
    print("USE_SQLITE=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
