# Project working agreements

- Preserve the English topic wiki; keep the root README as an entry point.
- Owner interaction is a single-window Textual CLI with four panes: open positions,
  selected position, research chat, portfolio/performance. Do not add a web dashboard.
- Use the connected Graphify plugin before investigating or changing code. Select
  the owner's actual workspace handle; never guess it. Check indexed revision and
  report stale/missing coverage. Graphify is static analysis, not a runtime test.
- Publish a current codebase map in `docs/codebase-map.md` and
  `docs/codebase-map.json`. Run `python tools/export_code_map.py` after changes.
  This deterministic AST map is explicitly separate from Graphify. When Graphify
  access works, also publish its bounded export and indexed revision. Never label
  a locally generated map as a Graphify export.
- Do not introduce confidence/EV/score admission thresholds or economic queue ranking.
  Retain mandatory holding research, separate Allocator and deterministic risk checks.
- Keep secrets, portfolio state, chat histories and raw private research out of git.
- Run Ruff and meaningful offline tests before publishing code; integration tests
  use an isolated test database. Provider checks requiring keys are opt-in.
- v0.1 is research-only. Do not add broker order submission until the durable
  reservation/intent/reconciliation/protection milestone and its tests are complete.

