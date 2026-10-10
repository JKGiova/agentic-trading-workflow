"""Export deterministic Python definitions/imports, without importing application modules.

This AST map is not a Graphify index. Graphify status/provenance is kept separately.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate() -> dict[str, str]:
    modules = {}
    for path in sorted((ROOT / "src/tradebot").glob("*.py")):
        module = "tradebot." + path.stem
        modules[module] = path
    nodes, edges, definitions = [], [], []
    hashes = {}
    for module, path in modules.items():
        source = path.read_text()
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(source.encode()).hexdigest()
        nodes.append({"id": module, "path": str(path.relative_to(ROOT))})
        tree = ast.parse(source)
        for item in ast.walk(tree):
            if isinstance(item, ast.ImportFrom) and item.module in modules:
                edges.append({"source": module, "target": item.module, "kind": "import"})
            if isinstance(item, ast.Import):
                for alias in item.names:
                    if alias.name in modules:
                        edges.append({"source": module, "target": alias.name, "kind": "import"})
        for item in tree.body:
            if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append(
                    {
                        "module": module,
                        "name": item.name,
                        "line": item.lineno,
                        "kind": "class" if isinstance(item, ast.ClassDef) else "function",
                    }
                )
                if isinstance(item, ast.ClassDef):
                    for member in item.body:
                        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            definitions.append(
                                {
                                    "module": module,
                                    "name": f"{item.name}.{member.name}",
                                    "line": member.lineno,
                                    "kind": "method",
                                }
                            )
    unique = sorted({(x["source"], x["target"]) for x in edges})
    edges = [{"source": a, "target": b, "kind": "import"} for a, b in unique]
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    graph = {
        "generator": "Python AST; not Graphify",
        "source_digest": digest,
        "source_hashes": hashes,
        "nodes": nodes,
        "links": edges,
        "definitions": definitions,
    }
    ids = {name: "M" + str(i) for i, name in enumerate(modules)}
    mermaid = ["flowchart TD"]
    for node in nodes:
        if node["id"].endswith(".__init__"):
            continue
        mermaid.append(f'    {ids[node["id"]]}["{node["id"].split(".")[-1]}"]')
    mermaid.extend(f"    {ids[x['source']]} --> {ids[x['target']]}" for x in edges)
    markdown = (
        "# Codebase map\n\n[Wiki home](README.md) · [CLI guide](cli.md)\n\n"
        "Generated from tracked Python source using `python tools/export_code_map.py`. "
        "The JSON includes file hashes, module imports and definitions. Import edges are "
        "static dependencies, not resolved call paths or test coverage.\n\n"
        "**Graphify:** uninstalled by the owner on 2026-10-10. "
        "No Graphify export or indexed commit is claimed. "
        "[Status record](graphify-status.json). This map is a separate AST export.\n\n"
        "```mermaid\n" + "\n".join(mermaid) + "\n```\n\n"
        "The CLI drives application services. Workflow uses model/retrieval adapters and "
        "deterministic risk previews; storage persists research and read-only snapshots. "
        "The broker adapter has no submission method.\n\n"
        "[Machine-readable map](codebase-map.json) contains "
        f"{len(nodes)} modules, {len(edges)} import edges and {len(definitions)} definitions.\n"
    )
    return {
        "docs/codebase-map.json": json.dumps(graph, indent=2) + "\n",
        "docs/codebase-map.md": markdown,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for name, body in generate().items():
        path = ROOT / name
        if args.check:
            if not path.exists() or path.read_text() != body:
                raise SystemExit(f"Stale code map: {name}; run export_code_map.py")
        else:
            path.write_text(body)


if __name__ == "__main__":
    main()
