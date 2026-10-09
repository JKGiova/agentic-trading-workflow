# Data sources, evidence, and memory

[Wiki home](README.md) · [Project overview](../README.md)

### Financial publications

Use selected financial publications through supported APIs, RSS feeds, or licensed data feeds. Examples to evaluate include Reuters, Financial Times, The Wall Street Journal, and Milano Finanza. Actual coverage depends on available access and compatible rights for retrieval, retention, and model processing.

Do not assume that a public headline permits storing or forwarding the full article. Preserve provider-specific usage restrictions, and process only content available through authorized access.

### Primary sources

Prioritize company investor-relations releases, earnings reports, regulatory filings, central-bank announcements, and official economic releases when available. Distinguish original disclosures from commentary and articles repeating them.

### X accounts

Maintain an explicit whitelist controlled by the project owners:

- Stable account ID and current username.
- Inclusion rules for original posts, replies, quote posts, and reposts.
- Approved topics or instruments where appropriate.
- Source configuration version and operational status.

Use the official X API with author filtering and incremental cursors. Recent Search covers the previous seven days; older historical coverage requires an appropriately authorized archive source or permitted retained data.

Being on the whitelist makes an account eligible for collection. Claims still require evaluation and, where appropriate, corroboration. Source permissions, API access, and content-retention obligations must be reviewed before enabling a connector.

## Evidence pipeline and persistent memory

For each source item, record:

- Provider, source item ID, account or publisher, and canonical URL.
- Publication time, first-seen time, fetch time, and revision time when available.
- The accessible text or permitted reference, language, and content hash.
- Related companies, instruments, topics, and event identifiers.
- Whether the item is an original disclosure, commentary, rumor, correction, or repeated report.
- Extraction results and the versions of the source connector and analysis configuration.

Deduplicate by source ID and content hash, then group reports concerning the same underlying event. Repeated coverage must not be counted as independent confirmation.

Each session receives three context layers:

| Layer | Contents |
| --- | --- |
| Recent information | Items first acquired within the last three hours, with publication-age labels, plus any unprocessed backlog |
| Relevant history | Earlier disclosures, related events, contradictory evidence, and previous context for the instruments under review |
| Position memory | Entry thesis, supporting evidence, invalidation conditions, review deadline, previous decisions, and execution outcomes |

Persist these layers independently of the LLM conversation. Retrieve relevant history by instrument, event, and time; add semantic retrieval if simpler filters prove insufficient.

Distinguish a newly published event from an old article discovered late. Preserve corrections and historical versions subject to source rules. During evaluation, use only the version that was available at the simulated decision time.

## Related pages

- [Mandatory holding research](analysis-team.md)
- [Forecasts and confidence](forecasts-and-confidence.md)
- [Source research](research.md)
