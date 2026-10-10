# First-run onboarding

[Wiki home](README.md) · [CLI](cli.md) · [Continuous runtime](continuous-runtime.md)

**Implemented in v0.3.0 on Python 3.14.** The default command opens a single terminal window for
Telegram setup and report scheduling. It does not require a policy file, stock watchlist, NVIDIA key,
broker credentials or running research agents.

```bash
tradingworkflow
```

Install the project and activate `.venv` first; see [installation](cli.md#install-and-connect-telegram).
Run commands from the repository directory to reuse the same saved setup.

On the first launch:

1. Create a Telegram bot with [@BotFather](https://t.me/BotFather), using `/newbot`.
2. Paste its token into the hidden input and choose **Connect and send test**.
3. Open the displayed bot link in your private Telegram chat and send the exact
   `/start <one-time-code>` shown in the terminal.
4. Receive the test message. The terminal confirms delivery and opens report scheduling.
5. Choose the hours between reports and press **Save report interval**. For example,
   `3` sends a report after each three-hour research cycle; `0.5` uses 30 minutes.

The token is checked through Telegram's `getMe` operation. Pairing accepts only the
matching code in a private chat where the sender ID matches the chat ID. A new bot
requires its own pairing. Failed token validation or cancelled pairing does not save
the entered token. After pairing, the token is saved before the test so an interrupted
test can be resumed from the connection home.

Later launches open the Telegram connection home without asking for the token again
or sending messages automatically. **Send test message** makes an explicit test;
**Change bot** reopens the token form; **Report interval** edits the saved schedule.
Ctrl+Q or Exit cancels active setup and closes clients.

## Report interval and starting analysis

The interval is saved with setup in the same research database. It overrides
`config.local.json`'s `session_hours` for `--supervisor`, including headless and
one-cycle modes. The news lookback (`news_hours`) remains a separate setting.
Intervals can range from one second to 8760 hours; normal operating intervals
should allow time for collection and model calls. Zero, negative, nonfinite and
unrepresentable intervals are rejected without changing the saved setting.

An existing v0.2 setup retains its paired chat and requests only the new interval
step. Editing the interval while the supervisor runs takes effect for the next
cycle. An open cycle retains its deadline, findings and frozen reporting boundary;
restarts preserve it. Other policy changes still require the original cycle policy.

After setting the NVIDIA key in `.env` and the selected stocks in
`config.local.json`, run:

```bash
tradingworkflow --supervisor --doctor
tradingworkflow --supervisor
# Or run the same team without the terminal interface:
tradingworkflow --supervisor --headless
```

The doctor checks the saved interval, model configuration and a matching Telegram
destination without contacting providers. Analysis startup requires a Telegram token
and paired chat (or an explicitly configured numeric chat ID). Setup itself makes no
model calls. Keep the supervisor process running; exiting it pauses collection and
delivery. Cycle reports are queued after synthesis completes, so provider latency
and Telegram quotas can delay delivery beyond the nominal cycle deadline.

## Commands

| Command | Behavior |
| --- | --- |
| `tradingworkflow` | First-run setup or saved Telegram connection home |
| `tradingworkflow --onboard` | Reopen the setup form with a masked saved token |
| `tradingworkflow --telegram-test` | Send one standalone test to the saved paired chat; no TUI |
| `tradingworkflow --demo` | Open the existing synthetic four-pane research terminal |
| `tradingworkflow --supervisor` | Run configured continuous research in the four-pane terminal |
| `tradingworkflow --session` | Open the older configured bounded-session research terminal |

Interactive setup needs a terminal, normally at least 80 columns by 24 rows.
Redirected/noninteractive input returns an instruction instead of hanging for a token.
The standalone test command works without interactive input after pairing. Advanced
research commands keep their explicit configuration requirements and do not run onboarding.

## Credentials and state

The app stores the token in `.tradebot/credentials.env`, using an atomic replacement
and owner-only permissions (0600 file, 0700 directory on POSIX). This is local
plaintext storage with restricted filesystem access, not an encrypted vault.
The directory is ignored by git. The app preserves other managed credential entries
and does not rewrite the owner's `.env`.

Credential precedence is explicit environment variables, managed credentials, then
the manual `.env`. If an exported token conflicts with one entered in the form,
setup asks you to update that environment variable rather than silently saving a
token that will be overridden at the next launch.

Pairing and completion metadata live in the selected SQLite/PostgreSQL database,
normally `.tradebot/research.db`; metadata contains a token fingerprint, not the
token. Changing the token invalidates its old pairing. `--database` selects the
same store for setup/tests/research; use it consistently when using a custom database.

Test messages have durable, separate notification IDs. Sending a test cannot flush
queued research reports. Research delivery does not replay old test notifications.
Quota responses retain a retry time; repeated clicks respect it. Timeout/crash
outcomes are unconfirmed and are not automatically resent. Check Telegram before
explicitly requesting another test. Completion requires confirmed delivery.

## Future product steps

Setup state is versioned and stores completion per capability. `REQUIRED_STEPS`
currently contains `telegram` and `report_schedule`. Future wallet/broker access and portfolio/configuration
screens should be registered as new steps when their actual runtime is available;
existing Telegram completion can be retained. The test suite verifies incremental
requirements and preservation of completed steps. No wallet keys or trading permissions
are collected by this release.

Future account steps must match the implemented broker permission mode and durable
execution milestone. Setup completion by itself never enables trading orders.

Tests cover masked UI at 80×24 and 120×36, redacted input/worker diagnostics,
first-run pairing/delivery, relaunch,
reconnection, invalid token, cancellation, secret-file replacement, rate limits,
unknown delivery, interval validation/editing, atomic preference updates, v0.2 migration,
provider independence and isolation from queued reports. Real
Telegram access still requires the owner's token and private chat interaction.

Primary protocol reference: [Telegram Bot API](https://core.telegram.org/bots/api).
