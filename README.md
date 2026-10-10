# Agentic Trading Workflow

A news-driven AI workflow for a selected group of stocks, with persistent evidence, mandatory position reviews, direct Bull/Bear debate, and a separate investment agent.

**Status: v0.3.0 on Python 3.14, with onboarding-configured Telegram reports.** Four analysts, a durable supervisor, NVIDIA NIM, Yahoo news discovery, peer review and periodic Telegram summaries are implemented, alongside the four-pane CLI and earlier bounded decision graphs. Live-provider access and prospective validation still require owner configuration.

## Install and run

```bash
git clone https://github.com/JKGiova/agentic-trading-workflow.git
cd agentic-trading-workflow
uv sync --locked --no-dev --python 3.14
source .venv/bin/activate
tradingworkflow
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) first if needed.
It creates `.venv`, installs Python 3.14 if needed and installs the locked runtime
dependencies. On macOS/Linux, activate the environment with the command above;
in Windows PowerShell use `.venv\Scripts\Activate.ps1`.

`tradingworkflow` opens Telegram onboarding on first run. Paste your BotFather token
in the hidden field, pair your private chat using the displayed `/start` code, and
receive a test message, then choose the hours between reports. Decimal intervals
are supported: `0.5` means every 30 minutes. Later launches reuse saved setup. This entry point runs
independently of the model/research team. See the [onboarding guide](docs/onboarding.md).

For later launches, `cd` into the repository, activate `.venv` and run
`tradingworkflow`. `deactivate` exits the environment. The optional `./start.sh`
launcher still installs dependencies and starts the same command automatically.

Use `tradingworkflow --demo` for the four-pane offline research demo, `--supervisor` for
configured continuous research, and `--session` for the older bounded terminal.
Pass `--onboard` to edit setup or `--telegram-test` to send one standalone test.
See the [CLI guide](docs/cli.md) for provider configuration.

After configuring the NVIDIA key and selected stocks, start the team with
`tradingworkflow --supervisor` (or add `--headless`). It continuously researches
news and sends a report for each completed X-hour cycle using the saved interval.
Keep the process running to receive reports. Open `tradingworkflow` and choose
**Report interval** to change X; any current cycle keeps its original deadline.

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

