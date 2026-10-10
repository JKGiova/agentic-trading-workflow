# Terminal interface and running v0.2.1

[Wiki home](README.md) · [Codebase map](codebase-map.md)

The release provides first-run Telegram onboarding and **research-only** agent modes,
including an explicit offline demo. All owner
interaction is through one terminal window. There is no web UI, and no broker order
submission method exists in this release.

## Install and connect Telegram

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then clone the
repository, install its locked runtime dependencies and activate the environment:

```bash
git clone https://github.com/JKGiova/agentic-trading-workflow.git
cd agentic-trading-workflow
uv sync --locked --no-dev --python 3.12
source .venv/bin/activate
tradingworkflow
```

`uv sync` creates `.venv`, downloads Python 3.12 if needed and installs the package,
including the `tradingworkflow` command, from `uv.lock`. Use `--python 3.13` to select
the other tested Python version. Activation is `source .venv/bin/activate` on
macOS/Linux and `.venv\Scripts\Activate.ps1` in Windows PowerShell.

For each later terminal session, return to the repository, activate `.venv` and run
`tradingworkflow`; no reinstall is needed. Use `deactivate` when finished. You can
also run `uv run --no-sync tradingworkflow` without activating the environment.
After pulling an update, rerun `uv sync --locked --no-dev` to refresh dependencies
and installed commands. Keep commands in the repository so local configuration and
state paths resolve consistently.

With an existing Python 3.12/3.13 and no `uv`, the standard Python installation is
also supported (dependency versions resolve from `pyproject.toml` rather than the lock):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
tradingworkflow
```

The optional `./start.sh` Bash launcher installs `uv` if needed into the ignored
`.tradebot/tools` directory, synchronizes the locked runtime dependencies and starts
`tradingworkflow` automatically. Bootstrap requires `curl` or `wget` and internet
access. It does not require sudo or modify shell profiles. Already-installed
development tools are retained. To select Python 3.13 with the launcher, use
`TRADEBOT_PYTHON=3.13 ./start.sh`. If executable permissions were lost when
downloading, use `bash start.sh`. The older `tradebot` command remains an alias.

No arguments opens Telegram onboarding: hidden token entry, private-chat pairing
and a test message. Later launches open the saved connection home. It requires no
NVIDIA or broker credentials and no policy file. See [onboarding](onboarding.md)
for secret storage, relaunch, cancellation and future wallet/configuration steps.
Choose research modes explicitly; `./start.sh` forwards these same arguments:

```bash
tradingworkflow --help
tradingworkflow --onboard
tradingworkflow --telegram-test
tradingworkflow --demo --doctor
tradingworkflow --demo --once
tradingworkflow --demo --auto
tradingworkflow --init
tradingworkflow --supervisor --doctor
tradingworkflow --supervisor --config config.local.json
tradingworkflow --session --config config.local.json
```

The research commands without `--demo` use provider configuration. Configure credentials as
described below before starting provider-backed research. Relative config/database
paths resolve from the current working directory; the optional Bash launcher always
switches to the repository directory before starting the command.

## Four-pane research terminal

The explicit `--demo` labels every position, news item, confidence and response as synthetic.
Its chatbot is a deterministic test double, not a paid AI model. Demo state is stored
in `.tradebot/demo.db`, separate from provider-backed research state. No Docker is needed.

| Pane | Interaction |
| --- | --- |
| Top left: open positions | Arrow keys or mouse select a holding; quantity, value and unrealized P/L |
| Top right: selected position | Thesis, initial/final confidence, research verdict, source coverage, evidence and allocation previews |
| Bottom left: research chatbot | Ask about the selected holding or portfolio; persistent conversation and read-only context |
| Bottom right: portfolio/performance | Equity, cash, pending buys, exposure, unrealized P/L, equity change and model spend |

`F1`–`F4` focus the panes. `Ctrl+R` runs a research session; `Ctrl+U` refreshes account
data; `Ctrl+Q` exits. The default 2×2 layout is tested at 80×24, 120×36 and 160×48.
Use at least 80×24; detail/performance content scrolls inside its pane. Chat and
research run asynchronously, leaving selection and navigation responsive.

The terminal refreshes account reads every 30 seconds. `--auto` schedules research
every configured `session_hours` while the terminal remains open; the first session
is manual. Continuous collection and worker/report scheduling are available with
`--supervisor`; see [continuous runtime](continuous-runtime.md).

```bash
tradingworkflow --demo --doctor
tradingworkflow --demo --once
tradingworkflow --demo --auto
```

## Configure provider-backed research

```bash
tradingworkflow --init
cp .env.example .env
# Edit config.local.json and .env locally.
tradingworkflow --doctor
tradingworkflow --session
```

`--init` creates a nonsecret policy template and refuses to overwrite it. Add selected
instruments, sectors, verified CIKs/aliases/authorized IR feed URLs, authorized market
search domains and the approved X author-ID/handle mapping. Supply the selected NVIDIA model credential (or explicitly selected OpenRouter),
Alpaca **paper**, X, Tavily and identifying SEC credentials in the private `.env`.
Choose your model/rates and financial/operating limits deliberately; the defaults
are prototype configuration, not personalized investment settings.

The doctor validates configuration without making provider requests or charging
credits. A successful doctor is not evidence that API entitlements work. Actual
authorization, feed coverage, model capabilities, response schemas, costs and latency
must be verified with your own accounts before relying on provider-backed research.

Provider reads include account/positions/open orders, IEX quotes, symbol-specific
Alpaca news, official X recent search, restricted-domain Tavily discovery, configured
SEC filing metadata and IR RSS. Filing metadata is labelled as metadata; full SEC
filings/company facts are not implemented. Date-less, failed or truncated searches
are recorded as incomplete. Articles are not assumed accessible through paywalls.

The chatbot uses the selected NVIDIA NIM adapter in provider mode and only receives a bounded snapshot,
selected stock's reports/evidence and recent conversation. Mentioning a single configured
ticker or company name can inspect a researched stock outside the open-position list.
It has no mutation,
shell, trading or unrestricted browsing tools. The runtime rejects unexpected
model tool calls; this initial chatbot answers from stored context rather than
performing a new live search on every question.

## Workflow implemented in this release

Every session researches the watchlist **union every holding**, including holdings
removed from the watchlist. Four analysts independently read frozen evidence; the
Financial Analyst's lead stage synthesizes initial confidence/scenarios. Holding
reviews precede optional debates. Each debate has independent Bull/Bear openings,
challenges, a bounded frozen-evidence reread/rebuttal and final cases, followed by
Orchestrator judgment. The separate Allocator chooses an action and investment request.

There is **no confidence/EV/score screening or queue ranking**. Least-recently-debated,
then symbol order determines the bounded queue; excess candidates remain pending.
Weak or missing initial estimates can enter debate. Unsupported final evidence,
scenario mass or verification defers added exposure.

The deterministic preview applies confidence sizing, stressed downside, cash reserve,
position/gross/sector limits, daily-loss stop, pending orders, freshness and no averaging
down. Other holdings are conservatively stressed at **100% loss** in v0.1 previews
until portfolio-wide stress estimates are implemented. Previews for separate stocks
do not reserve shared capital and must not be combined into executable orders.

All forecasts remain uncalibrated. The stored stage audit includes model, schema,
prompt version, frozen-input hash, reference price and information cutoff. Research
publication queries end at session start; per-stock information cutoff is capture
completion, not a historical claim that later-observed content was known earlier.
Historical retrieval respects both publication and observation times. Forecasts are
not yet settled against forward returns or corporate actions, and benchmark forecasts
are not implemented.

## Storage, budgets and failure behavior

SQLite/WAL is the local default. PostgreSQL uses the same initial SQLAlchemy schema:

```bash
tradingworkflow --session --database 'postgresql+psycopg://USER:PASSWORD@HOST/DATABASE'
```

Use a dedicated database and private credential handling; the example URL is a
placeholder. The v0.1 schema is created on startup. Alembic upgrades and the full
financial execution ledger remain later milestones.

Search attempts/evidence versions, session stages, fair queue, conversations and
model usage are durable. Completed stage outputs are immutable. v0.1 records failed
sessions but does not expose automatic crash-resume; start a fresh session on retry.
One database lease excludes concurrent decision sessions. Model calls have bounded
input/output and concurrency, one schema repair, no hidden model substitution and
an atomic monthly budget reservation. Unknown billed cost retains its conservative
reservation; configure endpoint rates and provider-console limits as well.

Provider read failures leave cached data visible with an error. Stale/unreconciled
state blocks added-exposure previews. Source gaps never automatically force a close.
Model failures leave cash/positions unchanged. Network orders, protection management,
durable order intents and reservation/fill reconciliation are **not implemented**.

Source requests have bounded pagination/timeouts, but separate provider-dollar/credit
reservations, shared multi-process SEC rate limits and independent five-minute
collection workers remain pending. Enabling repeated provider sessions can incur
news/search/X charges outside the model budget.

## Verification

```bash
uv run ruff check src tests tools
uv run ruff format --check src tests tools
uv run pytest --cov=tradebot --cov-fail-under=90
uv run python tools/export_code_map.py --check
```

Offline tests use HTTP fixtures and Textual Pilot; they never contact paid providers.
GitHub CI adds PostgreSQL 16 and Python 3.12/3.13. The PostgreSQL test drops only the
tables in the configured isolated test database; never point `TRADEBOT_TEST_DATABASE_URL`
at application state. Real API access checks remain opt-in and are not part of CI.

See [development status](development-status.md) for what is verified and still pending,
and [the backlog](implementation-backlog.md) for the retained full plan.

## Continuous team and Telegram (v0.2)

Use `tradingworkflow --supervisor` for the continuous team in the four-pane terminal,
`--supervisor --headless` for background operation, and `--telegram-pair` for the
private-chat pairing code. `--demo --supervisor --once` exercises a complete cycle
with an injected clock. Provider `--supervisor --once` waits for a real cycle.
See [continuous runtime](continuous-runtime.md) for credentials, optional-source
coverage, operating budgets and delivery recovery. In continuous mode Ctrl+R
collects news; it does not run the older bounded decision session.
