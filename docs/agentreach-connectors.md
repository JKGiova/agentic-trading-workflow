# Agent Reach web and X connectors

[Wiki home](README.md) · [Onboarding](onboarding.md) · [Provider plan](provider-plan.md)

**Implemented in v0.4.0 on Python 3.14.** The continuous analysis team retains
Yahoo/yfinance as its primary news discovery source. Analysts can read registered
article URLs through Agent Reach and collect approved-author X posts through its
selected Twitter backend. These capabilities run inside the existing typed tool
loop, evidence memory and report pipeline.

## Installed backends

| Capability | Installed implementation | Access |
| --- | --- | --- |
| Primary news discovery | Locked yfinance `Ticker.get_news` and `Search` | No account/login |
| Web page reading | Agent Reach 1.5.0 `WebChannel`, using Jina Reader | Public HTTPS pages; no publisher login or X cookies forwarded |
| X search | Agent Reach-selected twitter-cli 0.8.6 `TwitterClient.fetch_search` | Explicit `auth_token` and `ct0` from browser sign-in or manual export |
| Original disclosures | Existing SEC metadata and registered IR RSS | SEC contact identity and configured CIK/feed URLs |

Agent Reach is pinned to
[`94f06c1969dfc1834001269d79d3ad0972d9dee6`](https://github.com/Panniantong/Agent-Reach/tree/94f06c1969dfc1834001269d79d3ad0972d9dee6)
(MIT), and twitter-cli to
[`7c634e0d396b1e7af9f63315b414925fe4f29ae7`](https://github.com/public-clis/twitter-cli/tree/7c634e0d396b1e7af9f63315b414925fe4f29ae7)
(Apache-2.0). Both install with the project, including their declared dependencies;
there is no separate global tool installation. Git must be available to install
these pinned source dependencies. The package and lockfile agree on both revisions.

Agent Reach deliberately delegates X operations to upstream tools. Our adapter
uses its selected `TwitterClient` directly with explicit credentials; it does not
call the CLI authentication loader, which can otherwise inspect browser profiles
when cookies are missing or invalid. Agents cannot harvest browser profiles, log in,
post/like/follow, run arbitrary shell commands or auto-switch backends. The owner can
explicitly launch an isolated browser through [onboarding](browser-signin.md).
Jina Reader supplies page text, not an interactive local browser
or authenticated publisher session. Video transcripts and Exa search remain future
capabilities; yfinance supplies the current targeted search.

## Configure access

Run `tradingworkflow`, then complete the model and news screens. Existing paired
users retain Telegram and report scheduling and see only the added steps.

For X:

1. Choose **Install browser** once, then **Sign in to X** in news onboarding.
2. Complete login/verification in the dedicated browser. The app captures only
   `auth_token` and `ct0`, closes the browser and populates the masked field.
3. Alternatively, export **Header String** with Cookie-Editor and paste it in
   **X cookies**. Unrelated exported cookies are discarded.
4. Supply approved accounts as `numeric_id:handle`, separated by commas. Handles
   alone do not establish a verified identity. Example syntax: `123456:company`.
5. Save. This validates and stores configuration; it does not prove live access.

For web reading, register exact public article hostnames, for example
`www.nvidia.com, investor.nvidia.com`. These permissions allow reading only URLs
already present in the stock's supplied evidence; they do not grant arbitrary URL
navigation. Original company/event domains are particularly useful for following
conference announcements. Wildcards, full URLs and path expressions are rejected.

X and other news credentials are optional. **Configure later** records a deferred
step without enabling missing access. Missing X access remains an explicit report
gap. Blank fields retain saved credentials; reenter both X cookies to rotate them.
If they expire, return to **News credentials** and sign in again or replace them. Saving does not
print keys, run paid model calls or contact the providers. Restart the research
process to load changed credentials. Approved-author/domain changes are staged
for the next cycle; restarts retain the open cycle's original source policy.
A v0.3/v0.2 open cycle keeps its old official-X/direct-page backends until closure,
then switches to the configured v0.4 backends without changing its deadline.

Optional manual environment names are `TRADEBOT_X_AUTH_TOKEN` and
`TRADEBOT_X_CT0`. The application uses its private credentials file, not a shared
`~/.agent-reach/config.yaml`, so other installed agents' settings are untouched.

## Execution and evidence rules

The adapter starts only `python -m tradebot.agentreach_worker`, without a shell.
Credentials travel through stdin, not process arguments, prompts or diagnostic
messages. Requests are bounded to 16 KiB, response JSON/page content to 2 MB and
worker lifetime to 30 seconds. Cancellation or timeout kills and awaits the child;
raw stderr/provider errors are discarded. X calls are serialized per adapter and
backend automatic retries are disabled.

X searches use approved handles, the fixed stock identity/aliases, Latest ordering
and broad day operators. Returned timestamps are parsed and checked against the
exact UTC lookback/cutoff, including intraday boundaries. Every accepted post must
match both numeric author ID and handle, contain a stock name/symbol/alias, have a
numeric post ID and an aware publication timestamp. Retweets/promoted posts are
excluded; duplicates are merged. Renamed/unapproved authors, malformed results or
the 50-post sample cap produce degraded coverage. Failures are recorded separately
from a successful empty sampled result. Sampling is never evidence of an exhaustive
archive, and the legacy official API's seven-day limit is not applied to this backend.

Web reads retain the registered-HTTPS and public-DNS checks. Returned Jina provenance
must name the requested URL; changed source URLs require separate registration.
Empty, oversized, recognizable paywall/login and CAPTCHA/challenge responses are
rejected. The public URL is sent to Jina's remote reader. Returned text is untrusted
source data, bounded before the existing evidence excerpt limit, and labelled
`agentreach_web`. Its publication timestamp remains the original discovery timestamp;
the read does not independently verify a publisher's publication time. X evidence
is labelled `agentreach_x` and retains author ID, canonical post URL and original time.

Explicit alternatives remain available through `x_backend: "official"` and
`article_backend: "direct"` in the policy. Their credentials/coverage behavior remain
separate; no automatic fallback silently changes authentication or source provenance.
The older bounded `--session` continues using its original adapters.

`tradingworkflow --supervisor --doctor` lists selected backends, cookie presence,
approved-author count and registered-domain count, without network requests. A
successful configuration check does not prove source access, quotas or completeness.

## Verification

Offline tests cover the actual installed backend interfaces, explicit-cookie dispatch,
worker stdin/error/output/time limits and cancellation, ID/handle validation, stock
relevance, exact timestamps, duplicates, sample caps, empty/failure distinction,
registered page reads and provenance/challenge/paywall handling. The full HTTP-fixture
path includes onboarding credentials, Yahoo/X discovery, analyst-requested web reading,
NVIDIA transport, all four analysts, two scheduled cycles and Telegram delivery.
Live X/NVIDIA/Telegram checks still require owner credentials; fixtures do not certify
account access or forecast quality.
