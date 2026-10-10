# Portfolio Manager agent

[Wiki home](README.md) · [Project overview](../README.md)

The Portfolio Manager is the target name for the existing Portfolio Allocator/Allocator role, with expanded volatility and portfolio assessment. It is the same eighth AI role, not an additional agent. After every-stock debate, it receives approved addition cases and all holding outcomes, then chooses position actions and investment in one portfolio-wide plan. Current v0.1 still uses the Allocator implementation and independent per-stock previews.

## Inputs and confidence assessment

For each eligible addition, provide both available confidence records, debate status and verdict, research coverage, Bull/Bear cases, Orchestrator verdict and revision reasons, scenario payoffs, invalidators, expiry, holdings, pending orders, free cash, and versioned policy.

The Allocator checks:

- Available initial/final estimates refer to the same measurable outcome and reference-price basis; an initially missing estimate is recorded explicitly.
- The required debate completed, final estimates are supportable/current, and the Orchestrator verdict is `APPROVE`.
- Final confidence is supported by traceable evidence, with uncertainty and calibration status disclosed.
- Confidence revisions address actual challenges or verified facts; a large unexplained increase is deferred for clarification.
- Expected net payoff, downside, concentration, timing, and cash availability support the proposed position.

It may reject a confident proposal that lacks portfolio fit, select a smaller investment, or defer unresolved evidence. It cannot overrule a research `REJECT` or `DEFER`, modify policy, rewrite probabilities, or repeatedly request revisions until a proposal passes. Clarification is bounded and must preserve prior records.

## Position choices

| Portfolio state | Available choices |
| --- | --- |
| Eligible stock without a holding | `OPEN` or `NO_ACTION`; `OPEN` requires debate approval and investment/risk validation |
| Existing holding | `REINFORCE`, `HOLD`, `REDUCE`, or `CLOSE` |
| Reinforcement proposal | The same bounded debate, investment review, and risk validation are mandatory before adding capital |
| Valid holding whose addition was rejected | Choose `HOLD`, `REDUCE`, or `CLOSE` from its researched thesis; rejection alone does not force an exit |
| Incomplete ordinary holding review | Mark review deferred; no added exposure; independent protection and deterministic risk reduction remain active |

The prototype is long-only. The agent chooses the eligible stock, action, and target exposure; Bear victory does not authorize a short.

## Market volatility and portfolio risk

Use timestamped Alpaca observations and deterministic measurement tools for stock/market volatility, liquidity/spreads and scenario stress. Record calculation method, lookback window, as-of time, price-adjustment convention and data coverage. The model interprets tool results; it does not invent a volatility value.

Evaluate correlated holdings, sector concentration, existing and pending exposure, available cash, reserve requirements, drawdown/loss limits and near-term event risk. A high-confidence case may receive less capital or no allocation if portfolio downside is excessive. Missing or stale material risk inputs defer added exposure. Do not change policy thresholds in response to model prose.

## Investment selection and tools

Use the Orchestrator's policy-eligible `p_final` and revised opportunity/downside record in [budget management](budget-management.md). Final confidence scales the position ceiling; a separate stressed-loss budget caps volatile exposure. Never substitute `p_initial` after debate. A favorable expected payoff can support a lower-confidence trade without implying a larger safe investment.

The deterministic sizing tool returns confidence ceiling, stressed-loss ceiling, current/pending exposure, cash/risk headroom, and maximum executable quantity. The agent proposes a positive amount at or below this limit, explaining any smaller amount using scenario downside, uncertainty, or portfolio fit. Under identical constraints, higher final confidence raises the ceiling; it does not guarantee a larger chosen investment.

Rank supported additions under the configured policy and build one coherent portfolio plan with existing-position changes. A structured plan contains:

| Field | Required value |
| --- | --- |
| Confidence lineage | Available initial/final record IDs, values, calibration status, outcome ID, and debate/research verdict |
| Confidence and opportunity assessment | Why final probability/payoffs are usable, robust edge/score, stressed loss, revision reasons, and residual uncertainty |
| Decision | Action plus `ACCEPT`, `REJECT`, or `DEFER` for the proposal |
| Investment | Desired total position, incremental notional/quantity, maximum permitted amount, and reason for sizing |
| Portfolio effects | Cash remaining, concentration, estimated downside, pending commitments, and applied constraints |
| Thesis and safeguards | Evidence, invalidators, protective requirements, review time, and expiry |

An agent's `ACCEPT` is a recommendation. Deterministic validators recompute quantities and constraints, reserve cash atomically, and authorize submission. They may reject or defer an otherwise accepted proposal. Only the execution service holds broker credentials.

## Holding management and portfolio-wide pass

Every analyzed holding report has a scheduled debate. Pass its completed outcome to the Manager even when additional investment was rejected: HOLD, REDUCE and CLOSE remain distinct from approval to add risk. Incomplete review/debate is explicitly deferred; it does not become a successful HOLD. Candidate reinforcements need supported final confidence, debate approval and investment/risk validation.

Independent protections and deterministic policy-triggered risk reduction remain available during the research cycle; they do not wait for the scheduled debate. Reconcile any such action before the Manager's final portfolio-wide pass. Preserve one action per stock and do not spend hypothetical exit proceeds.

## Related pages

- [Architecture](architecture.md)
- [Forecasts and confidence](forecasts-and-confidence.md)
- [Existing-position management](position-management.md)
- [Opportunity analysis](opportunity-analysis.md)
- [Budget management](budget-management.md)
- [Session workflow](session-workflow.md)

