# Analysis team and mandatory holding research

[Wiki home](README.md) · [Project overview](../README.md)

| Agent | Research responsibility | Required stock-level output |
| --- | --- | --- |
| Market Analyst | Broad market news: macro releases, rates, geopolitical events, index conditions, and market-wide risk | Explain which market events affect each stock, the transmission mechanism, direction, timing, and opposing evidence |
| Financial Analyst | Financial news: earnings versus available expectations, guidance, margins, debt, financing, valuation context, and sector or competitor financial developments | Explain changes to the financial outlook and whether the news is already reflected in price |
| Company Analyst | Company news: products, contracts, management, operations, litigation, regulation, acquisitions, and investor-relations disclosures | Identify company-specific catalysts, materiality, primary-source confirmation, and thesis invalidators |
| Social Analyst | Social news from approved X accounts and any separately authorized communities | Distinguish factual claims, rumors, sentiment, and repeated narratives; identify the original source and corroboration status |

The Financial and Company Analysts can examine the same earnings release from different perspectives. An event referenced by both remains one event, not two independent confirmations.

Throughout the X-hour cycle, analysts process items, persist original assessments and exchange bounded findings/questions as specified in [continuous analysis](continuous-analysis.md). Each specialist retains revisions and disagreement. At the deadline, publish a shared-context briefing and one synthesized report per stock with: news summary, evidence IDs, source coverage, relevant history, directional view over the agreed horizon, assumptions, contradictory evidence, and unresolved questions. A missing source or an empty search must be reported explicitly.

Social-only rumors cannot justify opening or reinforcing a position in the initial design.

## Bounded research and reusable context

Analysts start with yfinance leads and role-scoped stored history, then request targeted original sources through typed AgentReach-backed tools. A mentioned conference can trigger announcement/transcript research; the trigger is a material unanswered question, not a confidence admission threshold. Preserve original specialist assessments, cross-review messages, cited revisions and dissent in a versioned event archive. See [research workflow](research-workflow.md) and [memory and retrieval](memory-and-retrieval.md).

## Team synthesis and initial confidence

After the cycle manifest freezes and all available specialist assessments/revisions are recorded, the designated Analyst Lead synthesizes one stock forecast on behalf of the analysis team. Propose the Financial Analyst as lead initially; this adds a stage, not another agent. It reconciles conflicting evidence without averaging votes or treating duplicate news as independent confirmation.

The team emits `p_initial`: its initial probability of a positive forward net return over the defined horizon. Include the outcome definition, reference price, cost assumptions, evidence quality, opposing scenarios, calibration status, and expiry. Preserve each specialist's view and any disagreement. Return `INSUFFICIENT_EVIDENCE` when the estimate cannot be supported.

The team also publishes average positive/negative net payoffs, supported scenario probabilities, stressed downside, and uncertainty when supportable. These are inputs to [opportunity analysis inside the debate](opportunity-analysis.md), not a pre-debate filter. Low confidence, weak expected return, a low score, or missing initial estimates do not automatically skip debate; disclose gaps for Bull/Bear verification. The Orchestrator's research verdict and the Allocator's later assessment decide whether to proceed.

Every holding still receives its mandatory research and risk-reduction review, independently of the debate outcome. The team supplies a holding case comparing news with the entry thesis; the [Portfolio Manager](portfolio-allocator.md) owns the actual action.

## Mandatory research for existing holdings

Active research of held stocks is an enforced workflow requirement. An analyst cannot satisfy it by claiming that it searched or by reusing an old summary.

At cycle start, the runtime creates a coverage matrix for every held stock; execute it during the cycle and perform a closing freshness check under the configured maximum-age policy:

| Research task | Requirement |
| --- | --- |
| Market | Refresh relevant macro, index, sector, and event-calendar information; explain the connection to the holding |
| Financial | Run a stock-specific search for earnings, guidance, financial releases, financing, and relevant sector developments |
| Company | Run a stock-specific search using the ticker, company name, and relevant aliases; check available primary disclosures |
| Social | Query approved accounts for ticker/company references and related claims, within configured source permissions |

The retrieval service records the executed query or provider request, stock, category, cutoff, retrieval time, source status, matched items, and pagination completeness. An authorized broad market refresh may cover multiple holdings if stock relevance is explicit. Financial, company, and social lookups must be stock-specific.

Valid coverage states are `COMPLETE_WITH_RESULTS`, `COMPLETE_NO_NEW_RESULTS`, `DEGRADED`, and `FAILED`. A successful empty search means no matching items were found; it does not imply that the stock has no risk.

The workflow runtime validates the matrix before permitting ordinary position decisions. Retry missing tasks within a bounded source-call budget. Unresolved gaps block new exposure for affected instruments and mark the session incomplete. Independent protective orders and deterministic risk reduction remain active. Do not close a holding merely because a news connector failed.

Reserve research/report/debate capacity for holdings first. Every analyzed-stock report still creates a debate obligation; time/cost exhaustion leaves visible pending work, not a numerical filter or a silently skipped report.

## Related pages

- [Forecasts and confidence](forecasts-and-confidence.md)
- [Opportunity analysis](opportunity-analysis.md)
- [Position management](position-management.md)
- [Portfolio Manager](portfolio-allocator.md)
- [Data and sources](data-and-sources.md)

