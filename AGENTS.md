# Project working agreements

- Preserve the English topic wiki; keep the root README as an entry point.
- Owner interaction is a single-window Textual CLI with four panes: open positions,
  selected position, research chat, portfolio/performance. Do not add a web dashboard.
- Graphify was uninstalled by the owner on 2026-10-10; it is not required.
- Publish a current codebase map in `docs/codebase-map.md` and
  `docs/codebase-map.json`. Run `python tools/export_code_map.py` after changes.
  This deterministic AST map is static analysis, not a runtime test or Graphify export.
- Do not introduce confidence/EV/score admission thresholds or economic queue ranking.
  Retain mandatory holding research, every-stock debate obligations, the separate
  Portfolio Manager and deterministic risk checks. The target analysts collaborate
  continuously within X-hour research cycles; current v0.1 remains a bounded session.
- Keep secrets, portfolio state, chat histories and raw private research out of git.
- Run Ruff and meaningful offline tests before publishing code; integration tests
  use an isolated test database. Provider checks requiring keys are opt-in.
- v0.1 is research-only. Do not add broker order submission until the durable
  reservation/intent/reconciliation/protection milestone and its tests are complete.

