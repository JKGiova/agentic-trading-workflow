# Agentic Trading Workflow Wiki

[Project overview](../README.md)

This is the versioned project wiki. Each page covers one part of the design; implementation milestones and current progress are tracked separately. All content is in English.

**Status: design and planning.** No trading service or agent implementation is claimed.

## Start here

Read the architecture, analyst team, forecasts, opportunity screening, position management, debate, Portfolio Allocator, and budget management pages in that order. Use the implementation plan to choose the first development milestone.

## Pages

| Page | Purpose |
| --- | --- |
| [Architecture and scope](architecture.md) | Stock universe, eight agent roles, component ownership, and proposed stack |
| [Analyst team and mandatory research](analysis-team.md) | Market, financial, company, and social analysts; held-stock coverage requirements |
| [Forecasts and confidence](forecasts-and-confidence.md) | Initial and revised confidence, screening gates, outcome definitions, and calibration |
| [Opportunity screening](opportunity-screening.md) | Confidence plus payoff, robust expected return, downside, and debate priority |
| [Existing-position management](position-management.md) | Reinforce, reduce, close, hold, and thesis comparison |
| [Entry and reinforcement debate](new-entry-debate.md) | Bull/Bear roles, bounded rounds, verification, and revised confidence |
| [Portfolio Allocator](portfolio-allocator.md) | Agent assessment of confidence, position choice, investment, and tool boundaries |
| [Budget management](budget-management.md) | Confidence-based acceptance and investment, shared capital limits, and cash reservations |
| [Session workflow](session-workflow.md) | Scheduling, portfolio reconciliation, action sequencing, and proposal contracts |
| [Data and sources](data-and-sources.md) | Approved publications and X accounts, timestamps, deduplication, and memory |
| [Risk and execution](risk-and-execution.md) | Deterministic limits, protective orders, idempotency, and paper execution |
| [Validation](validation.md) | Prospective evaluation, debate comparisons, and operational checks |
| [Implementation plan](PLAN.md) | Milestones, acceptance criteria, and open decisions |
| [Development status](development-status.md) | What is documented, what is implemented, and the next milestone |
| [Source research](research.md) | Recommended repositories, their gaps, and primary documentation |

## Current design decisions

- Four specialist analysts cover market, financial, company, and authorized social news.
- Every open position requires fresh, recorded searches and an explicit coverage status.
- Stock forecasts have an explicit horizon and outcome; model confidence is labeled uncalibrated until validated.
- Existing positions can be reinforced, reduced, closed, or held unchanged.
- The analyst team owns initial confidence and payoff scenarios; a risk-adjusted opportunity screen decides whether an addition deserves debate.
- Two researchers debate passed additions; the Orchestrator revises confidence and payoffs for another opportunity screen.
- A separate Portfolio Allocator analyzes the revised confidence and chooses the action and investment.
- Confidence and net payoff jointly gate new exposure; final confidence scales investment within a stressed-loss budget; a shared budget ledger enforces cash reserves, pending commitments, and risk caps.
- Risk limits and execution are deterministic services, with paper trading as the first target.

## Documentation layout

The root README is the entry point. Design pages live under `docs/`, with `PLAN.md` for milestones and `development-status.md` for actual progress, following the structure of the Moonlight tvOS PyroWave workspace.
