# Stock forecasts and confidence

[Wiki home](README.md) · [Project overview](../README.md)

The Decision Manager synthesizes the four completed analyst reports into one forecast per stock. It reconciles conflicting evidence and preserves material disagreement; it does not average analyst votes or count repeated headlines.

A stock forecast contains:

| Field | Meaning |
| --- | --- |
| Stock and as-of time | Instrument, evidence cutoff, and fresh reference price |
| News summary | Brief recap across market, financial, company, and social evidence |
| Direction | Bullish, neutral, bearish, or insufficient evidence over the declared horizon |
| Forecast horizon | Explicit start and settlement times using the exchange calendar |
| Outcome definition | Exact measurable event being forecast |
| Probability estimate | Optional model estimate for that event, clearly labeled uncalibrated initially |
| Evidence quality | Strong, mixed, weak, or incomplete, with an explanation |
| Scenarios | Upside, central, and downside mechanisms, catalysts, and invalidators |
| Market reaction | Price movement since the event, spread, liquidity, and possible prior pricing-in |
| Supporting and opposing sources | Evidence IDs, URLs, publication times, and first-seen times |
| Disagreement and missing data | Material analyst conflicts and unresolved searches |
| Expiry | When the forecast must be refreshed before use |

Proposed initial probability target: the stock's total return over the fixed horizon exceeds its configured benchmark's total return by a predeclared round-trip cost hurdle. The target, reference price, benchmark, horizon, cost assumption, and settlement rule must be recorded before the result is known. Reforecasting creates a new record rather than overwriting the original.

Keep predictive confidence separate from evidence quality. A well-sourced event can still have uncertain price implications. Four agents agreeing is not four statistically independent forecasts.

Initially display a qualitative outlook and, when elicited, a percentage labeled **model estimate — uncalibrated**. Permit `INSUFFICIENT_EVIDENCE` instead of forcing a number. Probability alone must not approve a trade or determine its size.

As prospective paper outcomes accumulate, evaluate Brier score and reliability curves on held-out chronological periods, including sample sizes and baseline comparisons. Validate any calibrator out of sample; use calibrated probabilities only when the relevant model, prompt, horizon, and data regime support them. Revalidate after material changes.

Evaluate forecast outcomes independently of trade exits so closing a position does not erase or redefine the original forecasting target.

## Dashboard summary

The stock summary shows the stock, research coverage, latest news recap, outlook, forecast horizon, estimated probability and calibration label, evidence quality, important disagreement, invalidation conditions, and next review. Link each summary to the underlying analyst reports and evidence.

Missing evidence must be visible. Show a deferred forecast separately from a neutral view.

## Related pages

- [Analysis team](analysis-team.md)
- [New-entry debate](new-entry-debate.md)
- [Validation](validation.md)
