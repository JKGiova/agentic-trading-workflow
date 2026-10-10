# Codebase map

[Wiki home](README.md) · [CLI guide](cli.md)

Generated from tracked Python source using `python tools/export_code_map.py`. The JSON includes file hashes, module imports and definitions. Import edges are static dependencies, not resolved call paths or test coverage.

**Graphify:** uninstalled by the owner on 2026-10-10. No Graphify export or indexed commit is claimed. [Status record](graphify-status.json). This map is a separate AST export.

```mermaid
flowchart TD
    M1["broker"]
    M2["cli"]
    M3["contracts"]
    M4["models"]
    M5["research"]
    M6["risk"]
    M7["service"]
    M8["settings"]
    M9["storage"]
    M10["terminal"]
    M11["workflow"]
    M1 --> M3
    M1 --> M8
    M2 --> M7
    M2 --> M8
    M2 --> M9
    M2 --> M10
    M4 --> M3
    M4 --> M8
    M4 --> M9
    M5 --> M3
    M5 --> M8
    M6 --> M3
    M6 --> M8
    M7 --> M1
    M7 --> M3
    M7 --> M4
    M7 --> M5
    M7 --> M8
    M7 --> M9
    M7 --> M11
    M8 --> M3
    M9 --> M3
    M10 --> M7
    M11 --> M3
    M11 --> M6
    M11 --> M8
    M11 --> M9
```

The CLI drives application services. Workflow uses model/retrieval adapters and deterministic risk previews; storage persists research and read-only snapshots. The broker adapter has no submission method.

[Machine-readable map](codebase-map.json) contains 12 modules, 27 import edges and 138 definitions.
