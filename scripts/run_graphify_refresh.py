"""Rebuild Graphify AST graph and copy outputs to Obsidian vault."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.detect import detect
from graphify.extract import collect_files, extract

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "graphify-out"
VAULT_GRAPH = Path(r"D:\Obsidian\PC-Cursor-Vault\Graphify-property-broker-client-1")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    result = detect(ROOT)
    OUT.joinpath(".graphify_detect.json").write_text(
        json.dumps(result, ensure_ascii=False), encoding="utf-8"
    )

    code_files: list[Path] = []
    for f in result.get("files", {}).get("code", []):
        p = Path(f)
        code_files.extend(collect_files(p) if p.is_dir() else [p])

    ast = (
        extract(code_files, cache_root=ROOT, parallel=False)
        if code_files
        else {"nodes": [], "edges": [], "input_tokens": 0, "output_tokens": 0}
    )
    merged = {
        "nodes": ast["nodes"],
        "edges": ast["edges"],
        "hyperedges": [],
        "input_tokens": ast.get("input_tokens", 0),
        "output_tokens": ast.get("output_tokens", 0),
    }
    OUT.joinpath(".graphify_extract.json").write_text(
        json.dumps(merged, ensure_ascii=False), encoding="utf-8"
    )

    graph = build_from_json(merged, directed=False)
    communities = cluster(graph)
    score_all(graph, communities)

    graph_data = {
        "directed": False,
        "multigraph": False,
        "graph": {},
        "nodes": [{"id": n, **graph.nodes[n]} for n in graph.nodes],
        "links": [{"source": u, "target": v, **d} for u, v, d in graph.edges(data=True)],
        "hyperedges": [],
    }
    OUT.joinpath("graph.json").write_text(
        json.dumps(graph_data, ensure_ascii=False), encoding="utf-8"
    )

    dest_out = VAULT_GRAPH / "graphify-out"
    dest_out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT / "graph.json", dest_out / "graph.json")
    if (OUT / "manifest.json").exists():
        shutil.copy2(OUT / "manifest.json", dest_out / "manifest.json")

    print(
        "GRAPHIFY_DONE",
        len(graph_data["nodes"]),
        len(graph_data["links"]),
        file=__import__("sys").stdout,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
