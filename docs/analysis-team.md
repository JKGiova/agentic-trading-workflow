# Analysis team and mandatory holding research

[Wiki home](README.md) · [Project overview](../README.md)

| Agent | Research responsibility | Required stock-level output |
| --- | --- | --- |
| Market Analyst | Broad market news: macro releases, rates, geopolitical events, index conditions, and market-wide risk | Explain which market events affect each stock, the transmission mechanism, direction, timing, and opposing evidence |
| Financial Analyst | Financial news: earnings versus available expectations, guidance, margins, debt, financing, valuation context, and sector or competitor financial developments | Explain changes to the financial outlook and whether the news is already reflected in price |
| Company Analyst | Company news: products, contracts, management, operations, litigation, regulation, acquisitions, and investor-relations disclosures | Identify company-specific catalysts, materiality, primary-source confirmation, and thesis invalidators |
| Social Analyst | Social news from approved X accounts and any separately authorized communities | Distinguish factual claims, rumors, sentiment, and repeated narratives; identify the original source and corroboration status |

The Financial and Company Analysts can examine the same earnings release from different perspectives. An event referenced by both remains one event, not two independent confirmations.

Every analyst publishes a short shared-context briefing and a per-stock report with: news summary, evidence IDs, source coverage, relevant history, directional view over the agreed horizon, assumptions, contradictory evidence, and unresolved questions. A missing source or an empty search must be reported explicitly.

Social-only rumors cannot justify opening or reinforcing a position in the initial design.

## Mandatory research for existing holdings

Active research of held stocks is an enforced workflow requirement. An analyst cannot satisfy it by claiming that it searched or by reusing an old summary.

At session start, the orchestrator creates a coverage matrix for every held stock:

| Research task | Requirement |
| --- | --- |
| Market | Refresh relevant macro, index, sector, and event-calendar information; explain the connection to the holding |
| Financial | Run a stock-specific search for earnings, guidance, financial releases, financing, and relevant sector developments |
| Company | Run a stock-specific search using the ticker, company name, and relevant aliases; check available primary disclosures |
| Social | Query approved accounts for ticker/company references and related claims, within configured source permissions |

The retrieval service records the executed query or provider request, stock, category, cutoff, retrieval time, source status, matched items, and pagination completeness. An authorized broad market refresh may cover multiple holdings if stock relevance is explicit. Financial, company, and social lookups must be stock-specific.

Valid coverage states are `COMPLETE_WITH_RESULTS`, `COMPLETE_NO_NEW_RESULTS`, `DEGRADED`, and `FAILED`. A successful empty search means no matching items were found; it does not imply that the stock has no risk.

The orchestrator validates the matrix before permitting ordinary position decisions. Retry missing tasks within a bounded source-call budget. Unresolved gaps block new exposure for affected instruments and mark the session incomplete. Independent protective orders and deterministic risk reduction remain active. Do not close a holding merely because a news connector failed.

Prioritize research and review of holdings over optional new-entry debates when the session budget is exhausted. All selected stocks still require a coverage status; incomplete forecasts are explicitly deferred.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Position management](position-management.md)
- [Data and sources](data-and-sources.md)
