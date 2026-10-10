# Agentic Trading Workflow

A news-driven AI workflow for a selected group of stocks, with persistent evidence, mandatory position reviews, direct Bull/Bear debate, and a separate investment agent.

**Status: v0.2 continuous research team.** Four analysts, a durable supervisor, NVIDIA NIM, Yahoo news discovery, peer review and periodic Telegram summaries are implemented, alongside the four-pane CLI and earlier bounded decision graphs. Live-provider access and prospective validation still require owner configuration.

## Run the terminal

```bash
./start.sh
```

On macOS/Linux, the launcher installs `uv` if needed, Python 3.12 and the locked
runtime dependencies, then opens the offline demo. Pass CLI options directly, e.g.
`./start.sh --demo --once`. See the [CLI guide](docs/cli.md) for provider mode.

One window: open positions, selected-position focus, research chatbot, portfolio/performance. `F1`–`F4` focus panes, `Ctrl+R` researches, `Ctrl+U` refreshes and `Ctrl+Q` exits. The demo is explicitly synthetic; provider mode requires private credentials and configuration. See the [CLI guide](docs/cli.md) and [codebase map](docs/codebase-map.md).

## Workflow

1. Throughout each configurable X-hour cycle, four analysts continuously process **market, financial, company, and authorized social news**, share findings and persist research, including every holding.
2. At cycle end, the team freezes one report per analyzed stock with **initial confidence, payoff scenarios, and known gaps**, without a numerical prefilter.
3. Every analyzed stock enters a bounded **Bull/Bear debate**, including holdings, HOLD and NO_ACTION cases.
4. The **Orchestrator** defines revised confidence, payoffs, and an explained approve/defer/reject research verdict.
5. A separate **Portfolio Manager agent** evaluates final confidence, measured volatility, cash, pending commitments and portfolio exposure, then chooses position actions and investment amounts.
6. Deterministic budget and risk checks validate and reserve capital before paper execution.

The implemented [continuous runtime](docs/continuous-runtime.md) opens the next research cycle while closing reports and queuing every-stock debate obligations. Automatic closed-cycle debate/portfolio consumption and broker execution remain later milestones. The older bounded decision session is still available separately.

## Read first

The detailed plan lives in the **[project wiki](docs/README.md)**. The selected target uses Alpaca for broker/market data, yfinance for news leads, and AgentReach-backed tools for deeper research. Start with the [research workflow](docs/research-workflow.md), [persistent memory](docs/memory-and-retrieval.md), and [provider plan](docs/provider-plan.md); yfinance and the NVIDIA adapter now run in the continuous team; AgentReach provisioning remains pending. Start with the [concrete implementation stack](docs/implementation-stack.md) and [ordered backlog](docs/implementation-backlog.md) for the proposed Python/LangGraph build.

| Document | Purpose |
| --- | --- |
| [Architecture](docs/architecture.md) | Universe, roles, components, and proposed stack |
| [Analysis team](docs/analysis-team.md) | Four analysts and mandatory searches for held stocks |
| [Forecasts and confidence](docs/forecasts-and-confidence.md) | News recaps, probabilities, payoff scenarios, and calibration |
| [Opportunity analysis](docs/opportunity-analysis.md) | Confidence, payoff, costs, and downside examined inside debate |
| [Position management](docs/position-management.md) | Thesis review and reinforce/reduce/close/hold actions |
| [Stock report debate](docs/new-entry-debate.md) | Two researchers, revised confidence, verification, and judgment |
| [Portfolio Manager](docs/portfolio-allocator.md) | Separate agent choosing position actions and investments |
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

## Next milestone

Configure and verify real NVIDIA/Telegram access, then connect closed-cycle reports to the debate and Portfolio Manager pipeline. Continue the [backlog](docs/implementation-backlog.md) for AgentReach source access, durable execution and prospective validation. Current allocations remain nonexecutable research previews.

See [source research](docs/research.md) for TradingAgents, TradingCrew, TradeAgent, and AI Hedge Fund. No upstream code is adopted by this plan; review its specific license before reuse.

