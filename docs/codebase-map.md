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
    M8["onboarding"]
    M9["research"]
    M10["risk"]
    M11["service"]
    M12["settings"]
    M13["setup_terminal"]
    M14["storage"]
    M15["supervisor"]
    M16["telegram"]
    M17["terminal"]
    M18["workflow"]
    M1 --> M5
    M1 --> M14
    M2 --> M1
    M2 --> M5
    M3 --> M5
    M3 --> M12
    M4 --> M1
    M4 --> M8
    M4 --> M11
    M4 --> M12
    M4 --> M13
    M4 --> M14
    M4 --> M16
    M4 --> M17
    M6 --> M2
    M6 --> M5
    M6 --> M12
    M6 --> M14
    M7 --> M5
    M7 --> M9
    M7 --> M12
    M8 --> M1
    M8 --> M5
    M8 --> M12
    M8 --> M14
    M8 --> M16
    M9 --> M5
    M9 --> M12
    M10 --> M5
    M10 --> M12
    M11 --> M1
    M11 --> M3
    M11 --> M5
    M11 --> M6
    M11 --> M7
    M11 --> M9
    M11 --> M12
    M11 --> M14
    M11 --> M15
    M11 --> M16
    M11 --> M18
    M12 --> M5
    M13 --> M8
    M14 --> M5
    M15 --> M1
    M15 --> M2
    M15 --> M5
    M15 --> M6
    M15 --> M12
    M15 --> M14
    M15 --> M16
    M16 --> M1
    M16 --> M5
    M17 --> M11
    M18 --> M5
    M18 --> M10
    M18 --> M12
    M18 --> M14
```

The CLI drives application services. Workflow uses model/retrieval adapters and deterministic risk previews; storage persists research and read-only snapshots. The broker adapter has no submission method.

[Machine-readable map](codebase-map.json) contains 19 modules, 58 import edges and 257 definitions.
