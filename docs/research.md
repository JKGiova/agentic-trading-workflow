# Reference repositories and source research

[Wiki home](README.md) · [Project overview](../README.md)

The following projects are candidates for reuse or architectural study. The comparison was reviewed on **2026-10-09** using repository documentation and selected source files. It is not an end-to-end execution audit or a profitability assessment.

| Repository | Relevant capabilities | Fit for Agentic Trading Workflow | Gaps or checks |
| --- | --- | --- | --- |
| [TradingCrew](https://github.com/rminchev1/TradingCrew) | Documents multi-agent analysis, news and social sentiment, analysis every N hours, Alpaca integration, optional execution, and a portfolio dashboard | Closest documented match to the intended product | Verify scheduler and execution implementations; inspect X ingestion, whitelist enforcement, memory, and the three-hour evidence window |
| [TradeAgent](https://github.com/enving/TradeAgent) | LLM news sentiment combined with technical signals, multiple news providers, Alpaca paper trading, persistent logging, and risk controls | Strong candidate for the operational bot and risk/execution structure | Its inspected scheduled-scan script runs once per invocation, so periodic triggering needs an external scheduler; evaluate or add X collection and configurable evidence windows |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | Python/LangGraph analyst and research agents, news and sentiment analysis, portfolio context, persistent decision memory, and noninteractive CLI runs | Strong candidate for the analysis engine | Connect collection and execution services; its current documented social inputs include StockTwits and Reddit, so approved-account X collection needs evaluation |
| [AI Hedge Fund](https://github.com/virattt/ai-hedge-fund) | Roadmap documents persistent paper portfolios, session records, idempotent paper ticks, a kill switch, and backtesting | Useful reference for stateful sessions and the decision ledger | Built-in scheduling is in progress, social connectors and live broker integration are planned; verify current implementation before relying on those features |

### Recommended evaluation order

1. **TradingAgents:** first architectural reference for specialist analysts and Bull/Bear research. Its roles and source handling need adaptation to our four news categories and enforced holding coverage; research claims do not establish profitability for this system.
2. **TradingCrew:** inspect scheduled portfolio analysis and Alpaca integration as operational examples.
3. **TradeAgent:** inspect news ingestion, deterministic limits, execution adapters, and externally triggered scans.
4. **AI Hedge Fund:** study persistent sessions, idempotent paper ticks, and the event ledger.

Select one starting point after a small paper-only technical spike. Compare maintainability, licensing, test coverage, provider costs, temporal correctness, and the effort required to meet the exact source requirements. Check the license and notices of the specific revision before importing code. No upstream code is adopted by this plan.

## Pinned upstream inspection and reuse approach

The source/metadata review below used exact commits on **2026-10-09**, not moving branch names. README claims and selected source paths were checked; no dependency install, provider call, broker call, or full test suite was run.

| Project | Reviewed commit | License file | Inspected implementation | Adaptation required |
| --- | --- | --- | --- | --- |
| TradingAgents | [1394a3f](https://github.com/TauricResearch/TradingAgents/tree/1394a3f72aa4393e1a98f51b382434c4b4c2d972) | Apache-2.0 | `pyproject.toml`, `tradingagents/graph/setup.py`, README and LICENSE | Remap market/social/news/fundamentals into our four categories; add approved X adapter/holding matrix; replace extra risk-agent stages with our Orchestrator/Allocator and deterministic ledger |
| TradingCrew | [f76e744](https://github.com/rminchev1/TradingCrew/tree/f76e744720ff24de17638f4f9b3097fdb4c6885c) | Apache-2.0 | README and LICENSE; repository tree | Evaluate advertised Alpaca/UI/scheduler components individually; enforce our role, queue, timestamp, and source contracts |
| TradeAgent | [f5023d1](https://github.com/enving/TradeAgent/tree/f5023d1a932bdecfe4d8ccdfaae871b14c4d0fe0) | MIT | `run_scheduled_trading.py`, README and LICENSE | Inspected script runs a scan per invocation; assess the separate deployment triggers and execution/risk modules before reuse |
| AI Hedge Fund | [78b779c](https://github.com/virattt/ai-hedge-fund/tree/78b779c1389e2d1452dc29606d2c4126d859b964) | MIT | README, `ROADMAP.md`, LICENSE | Study paper-ledger/idempotent-tick concepts; its file ledger and approval flow are not our broker-backed transactional runtime |

Recommended implementation is a minimal custom LangGraph application, with TradingAgents as the first source-level reference. Its inspected graph contains Bull/Bear, Research Manager, Trader, three risk roles, and Portfolio Manager; it is not already our eight-role flow. Its dependency list requires Python >=3.11 and includes LangGraph; validate the chosen lock before importing modules.

T0 compares selective reuse with the smaller custom graph on identical evidence. Preserve upstream licenses/notices for any imported code and record the adopted revision and modified files. No upstream code or license change is introduced by this documentation update.

## Workflow and memory inspection: 2026-10-10

At the pinned TradingAgents revision above, also inspected `agents/analysts/turn.py`, `dataflows/vendors/yahoo/news.py`, and `memory/log.py`. The analyst binds tools with a bounded wrap-up path; Yahoo formats headline/summary/link and uses sampled Search fallback; memory stores decisions plus outcomes/reflections and filters lessons by resolution date. Our target adapts those patterns with exact intraday cutoffs, event knowledge and position-thesis retrieval.

Selected [AgentReach](https://github.com/Panniantong/Agent-Reach) as the capability/setup reference for web search, page reads, approved-X retrieval and available YouTube captions. Its underlying backends require separate pinning and access checks; it is not the graph or persistence layer. See [provider plan](provider-plan.md), [research workflow](research-workflow.md) and [memory design](memory-and-retrieval.md). Pinned Agent Reach and twitter-cli are now installed dependencies; see the
[implemented connector guide](agentreach-connectors.md). No upstream source files are vendored.

## Concrete tool research

The [implementation stack](implementation-stack.md) and [connector specification](connector-implementation.md) link official documentation for the proposed tools. [Runtime/storage](agent-runtime.md), [data contracts](persistence-and-contracts.md), [deployment/costs](deployment-and-costs.md), and [the backlog](implementation-backlog.md) turn that research into implementation choices.

Primary API access, endpoint capability, model latency, source completeness, and actual bills still require the operational T0 spike. Public documentation verification must not be presented as successful signed-in API testing.

## Documentation and source links

- [X Recent Search](https://docs.x.com/x-api/posts/search/quickstart/recent-search)
- [X search query construction](https://docs.x.com/x-api/posts/search/integrate/build-a-query)
- [X Full-Archive Search](https://docs.x.com/x-api/posts/search/quickstart/full-archive-search)
- [X API pricing](https://docs.x.com/x-api/getting-started/pricing)
- [X Developer Policy](https://docs.x.com/developer-terms/policy)
- [Alpaca paper trading](https://docs.alpaca.markets/us/docs/paper-trading)
- [Alpaca order handling and buying-power reservations](https://docs.alpaca.markets/us/docs/orders-at-alpaca)
- [scikit-learn probability calibration: reliability and scoring](https://scikit-learn.org/stable/modules/calibration.html)
- [TradeAgent scheduled-scan source](https://github.com/enving/TradeAgent/blob/main/run_scheduled_trading.py)
- [AI Hedge Fund implementation roadmap](https://github.com/virattt/ai-hedge-fund/blob/main/ROADMAP.md)

- [TradingAgents research paper: specialist analysts and Bull/Bear research](https://arxiv.org/abs/2412.20138)
- [Teaching Models to Express Their Uncertainty in Words: calibration research](https://arxiv.org/abs/2205.14334)

## Opportunity and risk references

The opportunity-score and sizing formulas are proposed paper policies to validate, not claims made by these sources.

- [Investor.gov: microcap liquidity and volatility risks](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/investor-2)
- [FINRA: liquidity, concentration, and investment risk](https://www.finra.org/investors/investing/investing-basics/risk)
- [MIT OpenCourseWare: law of large numbers and independent repeated trials](https://ocw.mit.edu/courses/6-0002-introduction-to-computational-thinking-and-data-science-fall-2016/5af20311b02eaab959fcdb7ffb5694d3_MIT6_0002F16_lec6.pdf)

## Related pages

- [Architecture](architecture.md)
- [Opportunity analysis](opportunity-analysis.md)
- [New-entry debate](new-entry-debate.md)
- [Implementation plan](PLAN.md)

