# Agentic Trading Workflow

A news-driven AI workflow for a selected group of stocks, with persistent evidence, mandatory position reviews, direct Bull/Bear debate, and a separate investment agent.

**Status: v0.1 research terminal.** A runnable four-pane CLI, explicit offline demo, research agents, source adapters and deterministic allocation previews are implemented. Network order submission and prospective performance validation remain later milestones.

## Run the terminal

```bash
uv sync --locked
uv run tradebot --demo
```

One window: open positions, selected-position focus, research chatbot, portfolio/performance. `F1`–`F4` focus panes, `Ctrl+R` researches, `Ctrl+U` refreshes and `Ctrl+Q` exits. The demo is explicitly synthetic; provider mode requires private credentials and configuration. See the [CLI guide](docs/cli.md) and [codebase map](docs/codebase-map.md).

## Workflow

1. Every configurable X hours, four analysts research **market, financial, company, and authorized social news**, including every holding.
2. The analysis team publishes **initial confidence, payoff scenarios, and known gaps**, without a numerical prefilter.
3. Admissible openings and reinforcements enter a bounded **Bull/Bear debate**, which directly evaluates confidence, potential, losses, costs, and uncertainty.
4. The **Orchestrator** defines revised confidence, payoffs, and an explained approve/defer/reject research verdict.
5. A separate **Portfolio Allocator agent** analyzes that confidence and chooses position actions and investment amounts. Existing holdings also receive hold/reduce/close reviews.
6. Deterministic budget and risk checks validate and reserve capital before paper execution.

News collection and order monitoring run independently of AI sessions. Research uses the latest three-hour window, relevant history, and unprocessed backlog.

## Read first

The detailed plan lives in the **[project wiki](docs/README.md)**. Start with the [concrete implementation stack](docs/implementation-stack.md) and [ordered backlog](docs/implementation-backlog.md) for the proposed Python/LangGraph build.

| Document | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Universe, roles, components, and proposed stack |
| [Analysis team](docs/analysis-team.md) | Four analysts and mandatory searches for held stocks |
| [Forecasts and confidence](docs/forecasts-and-confidence.md) | News recaps, probabilities, payoff scenarios, and calibration |
| [Opportunity analysis](docs/opportunity-analysis.md) | Confidence, payoff, costs, and downside examined inside debate |
| [Position management](docs/position-management.md) | Thesis review and reinforce/reduce/close/hold actions |
| [Entry and reinforcement debate](docs/new-entry-debate.md) | Two researchers, revised confidence, verification, and judgment |
| [Portfolio Allocator](docs/portfolio-allocator.md) | Separate agent choosing position actions and investments |
| [Budget management](docs/budget-management.md) | Confidence-based sizing, downside budgets, capital limits, and reservations |
| [Implementation plan](docs/PLAN.md) | Milestones, acceptance criteria, and open decisions |
| [Development status](docs/development-status.md) | Completed documentation and pending implementation |
| [Source research](docs/research.md) | Recommended upstream repositories and verified references |

Implementation details cover [connectors](docs/connector-implementation.md), [agent runtime](docs/agent-runtime.md), [storage/contracts](docs/persistence-and-contracts.md), and [deployment/cost estimates](docs/deployment-and-costs.md).

The wiki also covers [session scheduling](docs/session-workflow.md), [data and memory](docs/data-and-sources.md), [risk and execution](docs/risk-and-execution.md), and [validation](docs/validation.md).

## Repository layout

- `README.md`: project overview and navigation.
- `docs/`: versioned design wiki, research, roadmap, and development status.
- `src/tradebot/`: terminal, services, research workflow, adapters, contracts, risk and persistence.
- `tests/`: offline workflow/provider fixtures, terminal interaction and isolated PostgreSQL tests.
- `tools/`: deterministic code map export; Graphify provenance is recorded separately.
- `LICENSE`: repository license.

## First milestone

Continue [T0 and the backlog](docs/implementation-backlog.md): prove actual authorized source/model/account access, then implement independent collectors, durable execution/recovery and prospective validation. The initial custom graph is runnable; all current allocations are nonexecutable research previews.

See [source research](docs/research.md) for TradingAgents, TradingCrew, TradeAgent, and AI Hedge Fund. No upstream code is adopted by this plan; review its specific license before reuse.

