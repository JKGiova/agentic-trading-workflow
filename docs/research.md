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
- [Opportunity screening](opportunity-screening.md)
- [New-entry debate](new-entry-debate.md)
- [Implementation plan](PLAN.md)
