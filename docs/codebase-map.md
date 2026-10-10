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
    M6["browser_signin"]
    M7["cli"]
    M8["contracts"]
    M9["models"]
    M10["news_sources"]
    M11["onboarding"]
    M12["research"]
    M13["risk"]
    M14["service"]
    M15["settings"]
    M16["setup_terminal"]
    M17["storage"]
    M18["supervisor"]
    M19["telegram"]
    M20["terminal"]
    M21["workflow"]
    M1 --> M8
    M1 --> M12
    M3 --> M8
    M3 --> M17
    M4 --> M3
    M4 --> M8
    M5 --> M8
    M5 --> M15
    M6 --> M11
    M7 --> M1
    M7 --> M3
    M7 --> M11
    M7 --> M14
    M7 --> M15
    M7 --> M16
    M7 --> M17
    M7 --> M19
    M7 --> M20
    M9 --> M4
    M9 --> M8
    M9 --> M15
    M9 --> M17
    M10 --> M1
    M10 --> M8
    M10 --> M12
    M10 --> M15
    M11 --> M3
    M11 --> M8
    M11 --> M15
    M11 --> M17
    M11 --> M19
    M12 --> M8
    M12 --> M15
    M13 --> M8
    M13 --> M15
    M14 --> M3
    M14 --> M5
    M14 --> M8
    M14 --> M9
    M14 --> M10
    M14 --> M12
    M14 --> M15
    M14 --> M17
    M14 --> M18
    M14 --> M19
    M14 --> M21
    M15 --> M8
    M16 --> M6
    M16 --> M11
    M17 --> M8
    M18 --> M3
    M18 --> M4
    M18 --> M8
    M18 --> M9
    M18 --> M15
    M18 --> M17
    M18 --> M19
    M19 --> M3
    M19 --> M8
    M20 --> M14
    M21 --> M8
    M21 --> M13
    M21 --> M15
    M21 --> M17
```

The CLI drives application services. Workflow uses model/retrieval adapters and deterministic risk previews; storage persists research and read-only snapshots. The broker adapter has no submission method.

[Machine-readable map](codebase-map.json) contains 22 modules, 64 import edges and 289 definitions.
