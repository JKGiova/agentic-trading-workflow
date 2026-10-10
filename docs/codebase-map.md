# Codebase map

[Wiki home](README.md) · [CLI guide](cli.md)

Generated from tracked Python source using `python tools/export_code_map.py`. The JSON includes file hashes, module imports and definitions. Import edges are static dependencies, not resolved call paths or test coverage.

**Graphify:** uninstalled by the owner on 2026-10-10. No Graphify export or indexed commit is claimed. [Status record](graphify-status.json). This map is a separate AST export.

```mermaid
flowchart TD
    M1["analysis_memory"]
    M2["analysts"]
    M3["broker"]
    M4["cli"]
    M5["contracts"]
    M6["models"]
    M7["news_sources"]
    M8["research"]
    M9["risk"]
    M10["service"]
    M11["settings"]
    M12["storage"]
    M13["supervisor"]
    M14["telegram"]
    M15["terminal"]
    M16["workflow"]
    M1 --> M5
    M1 --> M12
    M2 --> M1
    M2 --> M5
    M3 --> M5
    M3 --> M11
    M4 --> M1
    M4 --> M10
    M4 --> M11
    M4 --> M12
    M4 --> M14
    M4 --> M15
    M6 --> M2
    M6 --> M5
    M6 --> M11
    M6 --> M12
    M7 --> M5
    M7 --> M8
    M7 --> M11
    M8 --> M5
    M8 --> M11
    M9 --> M5
    M9 --> M11
    M10 --> M1
    M10 --> M3
    M10 --> M5
    M10 --> M6
    M10 --> M7
    M10 --> M8
    M10 --> M11
    M10 --> M12
    M10 --> M13
    M10 --> M14
    M10 --> M16
    M11 --> M5
    M12 --> M5
    M13 --> M1
    M13 --> M2
    M13 --> M5
    M13 --> M6
    M13 --> M11
    M13 --> M12
    M13 --> M14
    M14 --> M1
    M15 --> M10
    M16 --> M5
    M16 --> M9
    M16 --> M11
    M16 --> M12
```

The CLI drives application services. Workflow uses model/retrieval adapters and deterministic risk previews; storage persists research and read-only snapshots. The broker adapter has no submission method.

[Machine-readable map](codebase-map.json) contains 17 modules, 49 import edges and 215 definitions.
