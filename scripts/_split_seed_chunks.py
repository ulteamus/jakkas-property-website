#!/usr/bin/env python3
"""Split seed SQL into ~8KB chunks for MCP execute_sql."""
from pathlib import Path

src = Path("scripts/_seed_cloud.sql")
lines = src.read_text(encoding="utf-8").splitlines()
chunks: list[list[str]] = []
cur: list[str] = []
size = 0
for ln in lines:
    if size + len(ln) > 7000 and cur:
        chunks.append(cur)
        cur = []
        size = 0
    cur.append(ln)
    size += len(ln) + 1
if cur:
    chunks.append(cur)

out_dir = Path("scripts/_seed_chunks")
out_dir.mkdir(exist_ok=True)
for i, ch in enumerate(chunks):
    p = out_dir / f"chunk_{i:02d}.sql"
    p.write_text("\n".join(ch) + "\n", encoding="utf-8")
    print(f"{p.name} lines={len(ch)} chars={p.stat().st_size}")
print("total_chunks", len(chunks))
