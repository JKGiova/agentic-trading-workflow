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

## Team synthesis and initial confidence

After all independent reports are complete, the designated Analyst Lead synthesizes one stock forecast on behalf of the analysis team. Propose the Financial Analyst as lead initially; this adds a stage, not another agent. It reconciles conflicting evidence without averaging votes or treating duplicate news as independent confirmation.

The team emits `p_initial`: its initial probability of a positive forward net return over the defined horizon. Include the outcome definition, reference price, cost assumptions, evidence quality, opposing scenarios, calibration status, and expiry. Preserve each specialist's view and any disagreement. Return `INSUFFICIENT_EVIDENCE` when the estimate cannot be supported.

The deterministic first gate rejects an `OPEN` or `REINFORCE` proposal immediately when a valid `p_initial <= p_initial_min`. No Bull/Bear debate or investment selection runs for that rejected addition. Missing or invalid confidence defers it. Reconsideration requires a new versioned review after material new evidence or the next scheduled session, not retries until the threshold is crossed.

Every holding still receives its mandatory research and risk-reduction review, regardless of the first gate. The team supplies a holding case comparing news with the entry thesis; the [Portfolio Allocator](portfolio-allocator.md) owns the actual action.

## Mandatory research for existing holdings

Active research of held stocks is an enforced workflow requirement. An analyst cannot satisfy it by claiming that it searched or by reusing an old summary.

At session start, the workflow runtime creates a coverage matrix for every held stock:

| Research task | Requirement |
| --- | --- |
| Market | Refresh relevant macro, index, sector, and event-calendar information; explain the connection to the holding |
| Financial | Run a stock-specific search for earnings, guidance, financial releases, financing, and relevant sector developments |
| Company | Run a stock-specific search using the ticker, company name, and relevant aliases; check available primary disclosures |
| Social | Query approved accounts for ticker/company references and related claims, within configured source permissions |

The retrieval service records the executed query or provider request, stock, category, cutoff, retrieval time, source status, matched items, and pagination completeness. An authorized broad market refresh may cover multiple holdings if stock relevance is explicit. Financial, company, and social lookups must be stock-specific.

Valid coverage states are `COMPLETE_WITH_RESULTS`, `COMPLETE_NO_NEW_RESULTS`, `DEGRADED`, and `FAILED`. A successful empty search means no matching items were found; it does not imply that the stock has no risk.

The workflow runtime validates the matrix before permitting ordinary position decisions. Retry missing tasks within a bounded source-call budget. Unresolved gaps block new exposure for affected instruments and mark the session incomplete. Independent protective orders and deterministic risk reduction remain active. Do not close a holding merely because a news connector failed.

Prioritize research and review of holdings over optional new-entry debates when the session budget is exhausted. All selected stocks still require a coverage status; incomplete forecasts are explicitly deferred.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Position management](position-management.md)
- [Portfolio Allocator](portfolio-allocator.md)
- [Data and sources](data-and-sources.md)
