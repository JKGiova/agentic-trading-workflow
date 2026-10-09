# Agentic Trading Workflow

A news-driven AI workflow for a selected group of stocks, with persistent evidence, mandatory position reviews, two-stage opportunity screening, Bull/Bear debate, and a separate investment agent.

**Status: design and planning.** The initial target is long-only paper trading. Agent services, data connectors, broker execution, and performance evaluation remain planned.

## Workflow

1. Every configurable X hours, four analysts research **market, financial, company, and authorized social news**, including every holding.
2. The analysis team publishes **initial confidence and payoff scenarios**. A screen combines expected net return, uncertainty, and downside to select debate candidates.
3. Eligible openings and reinforcements face a bounded **Bull/Bear debate**.
4. The **Orchestrator** defines revised confidence, payoffs, and a verdict; a second opportunity gate applies.
5. A separate **Portfolio Allocator agent** analyzes that confidence and chooses position actions and investment amounts. Existing holdings also receive hold/reduce/close reviews.
6. Deterministic budget and risk checks validate and reserve capital before paper execution.

News collection and order monitoring run independently of AI sessions. Research uses the latest three-hour window, relevant history, and unprocessed backlog.

## Read first

The detailed plan lives in the **[project wiki](docs/README.md)**.

| Document | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Universe, roles, components, and proposed stack |
| [Analysis team](docs/analysis-team.md) | Four analysts and mandatory searches for held stocks |
| [Forecasts and confidence](docs/forecasts-and-confidence.md) | News recaps, probabilities, payoff scenarios, and calibration |
| [Opportunity screening](docs/opportunity-screening.md) | Confidence, upside/downside, and expected return relative to stressed loss |
| [Position management](docs/position-management.md) | Thesis review and reinforce/reduce/close/hold actions |
| [Entry and reinforcement debate](docs/new-entry-debate.md) | Two researchers, revised confidence, verification, and judgment |
| [Portfolio Allocator](docs/portfolio-allocator.md) | Separate agent choosing position actions and investments |
| [Budget management](docs/budget-management.md) | Confidence-based sizing, downside budgets, capital limits, and reservations |
| [Implementation plan](docs/PLAN.md) | Milestones, acceptance criteria, and open decisions |
| [Development status](docs/development-status.md) | Completed documentation and pending implementation |
| [Source research](docs/research.md) | Recommended upstream repositories and verified references |

The wiki also covers [session scheduling](docs/session-workflow.md), [data and memory](docs/data-and-sources.md), [risk and execution](docs/risk-and-execution.md), and [validation](docs/validation.md).

## Repository layout

- `README.md`: project overview and navigation.
- `docs/`: versioned design wiki, research, roadmap, and development status.
- `LICENSE`: repository license.

## First milestone

Choose the stock watchlist, forecast horizon, evidence sources, opportunity-screen thresholds, portfolio/model budgets, and broker candidate. Evaluate one upstream in a reproducible paper-only spike before implementing the workflow.

See [source research](docs/research.md) for TradingAgents, TradingCrew, TradeAgent, and AI Hedge Fund. No upstream code is adopted by this plan; review its specific license before reuse.
