# Codebase map

[Wiki home](README.md) · [CLI guide](cli.md)

Generated from tracked Python source using `python tools/export_code_map.py`. The JSON includes file hashes, module imports and definitions. Import edges are static dependencies, not resolved call paths or test coverage.

**Graphify:** uninstalled by the owner on 2026-10-10. No Graphify export or indexed commit is claimed. [Status record](graphify-status.json). This map is a separate AST export.

```mermaid
flowchart TD
    M1["agentreach_sources"]
    M2["agentreach_worker"]
    M3["analysis_memory"]
    M4["analysts"]
    M5["broker"]
    M6["cli"]
    M7["contracts"]
    M8["models"]
    M9["news_sources"]
    M10["onboarding"]
    M11["research"]
    M12["risk"]
    M13["service"]
    M14["settings"]
    M15["setup_terminal"]
    M16["storage"]
    M17["supervisor"]
    M18["telegram"]
    M19["terminal"]
    M20["workflow"]
    M1 --> M7
    M1 --> M11
    M3 --> M7
    M3 --> M16
    M4 --> M3
    M4 --> M7
    M5 --> M7
    M5 --> M14
    M6 --> M1
    M6 --> M3
    M6 --> M10
    M6 --> M13
    M6 --> M14
    M6 --> M15
    M6 --> M16
    M6 --> M18
    M6 --> M19
    M8 --> M4
    M8 --> M7
    M8 --> M14
    M8 --> M16
    M9 --> M1
    M9 --> M7
    M9 --> M11
    M9 --> M14
    M10 --> M3
    M10 --> M7
    M10 --> M14
    M10 --> M16
    M10 --> M18
    M11 --> M7
    M11 --> M14
    M12 --> M7
    M12 --> M14
    M13 --> M3
    M13 --> M5
    M13 --> M7
    M13 --> M8
    M13 --> M9
    M13 --> M11
    M13 --> M14
    M13 --> M16
    M13 --> M17
    M13 --> M18
    M13 --> M20
    M14 --> M7
    M15 --> M10
    M16 --> M7
    M17 --> M3
    M17 --> M4
    M17 --> M7
    M17 --> M8
    M17 --> M14
    M17 --> M16
    M17 --> M18
    M18 --> M3
    M18 --> M7
    M19 --> M13
    M20 --> M7
    M20 --> M12
    M20 --> M14
    M20 --> M16
```

The CLI drives application services. Workflow uses model/retrieval adapters and deterministic risk previews; storage persists research and read-only snapshots. The broker adapter has no submission method.

[Machine-readable map](codebase-map.json) contains 21 modules, 62 import edges and 280 definitions.
