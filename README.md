# Agentic Trading Workflow

A news-driven AI workflow for a selected group of stocks, with persistent evidence, mandatory position reviews, and a two-agent debate for new entries.

**Status: design and planning.** The initial target is long-only paper trading. Agent services, data connectors, broker execution, and performance evaluation remain planned.

## Workflow

1. Every configurable X hours, four analysts research **market, financial, company, and authorized social news**.
2. The Decision Manager publishes a news recap and forecast for each selected stock, with a defined horizon, evidence, and labeled confidence.
3. Every open position receives mandatory fresh research and a **reinforce, reduce, close, or hold** review.
4. New-entry candidates face a bounded **Bull/Bear debate** and an approve/defer/reject verdict.
5. Deterministic portfolio limits validate proposals before paper execution.

News collection and order monitoring run independently of AI sessions. Research uses the latest three-hour window, relevant history, and unprocessed backlog.

## Read first

The detailed plan lives in the **[project wiki](docs/README.md)**.

| Document | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Universe, roles, components, and proposed stack |
| [Analysis team](docs/analysis-team.md) | Four analysts and mandatory searches for held stocks |
| [Forecasts and confidence](docs/forecasts-and-confidence.md) | News recaps, horizon, probabilities, and calibration |
| [Position management](docs/position-management.md) | Thesis review and reinforce/reduce/close/hold actions |
| [New-entry debate](docs/new-entry-debate.md) | Two researchers, bounded rounds, verification, and judgment |
| [Implementation plan](docs/PLAN.md) | Milestones, acceptance criteria, and open decisions |
| [Development status](docs/development-status.md) | Completed documentation and pending implementation |
| [Source research](docs/research.md) | Recommended upstream repositories and verified references |

The wiki also covers [session scheduling](docs/session-workflow.md), [data and memory](docs/data-and-sources.md), [risk and execution](docs/risk-and-execution.md), and [validation](docs/validation.md).

## Repository layout

- `README.md`: project overview and navigation.
- `docs/`: versioned design wiki, research, roadmap, and development status.
- `LICENSE`: repository license.

## First milestone

Choose the stock watchlist, forecast horizon, evidence sources, model budget, and broker candidate. Evaluate one upstream in a reproducible paper-only spike before implementing the workflow.

See [source research](docs/research.md) for TradingAgents, TradingCrew, TradeAgent, and AI Hedge Fund. No upstream code is adopted by this plan; review its specific license before reuse.
