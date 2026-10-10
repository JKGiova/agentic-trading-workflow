"""All owner interaction is through this CLI and the single-window terminal."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from tradebot.service import TradeService, demo_policy
from tradebot.settings import Credentials, Policy, ReportSchedule
from tradebot.storage import Store
from tradebot.terminal import TradingTerminal


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Four-pane stock research terminal (orders disabled)"
    )
    result.add_argument("--demo", action="store_true", help="Explicit synthetic offline demo")
    result.add_argument("--config", type=Path, default=Path("config.local.json"))
    result.add_argument("--database", help="SQLAlchemy SQLite or postgresql+psycopg URL")
    result.add_argument(
        "--doctor", action="store_true", help="Local configuration check; no API calls"
    )
    result.add_argument(
        "--once", action="store_true", help="One research session as JSON, without TUI"
    )
    result.add_argument(
        "--auto", action="store_true", help="Schedule sessions every configured X hours"
    )
    result.add_argument("--init", action="store_true", help="Create a nonsecret config template")
    result.add_argument("--session", action="store_true", help="Open bounded research terminal")
    setup = result.add_mutually_exclusive_group()
    setup.add_argument("--onboard", action="store_true", help="Open Telegram setup again")
    setup.add_argument(
        "--telegram-test", action="store_true", help="Send one test to the saved private chat"
    )
    result.add_argument(
        "--supervisor", action="store_true", help="Continuous four-analyst research team"
    )
    result.add_argument("--headless", action="store_true", help="Run supervisor without TUI")
    result.add_argument(
        "--telegram-pair",
        action="store_true",
        help="Pair your private Telegram chat using a one-time code",
    )
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    if args.init:
        if args.config.exists():
            print("Config already exists; no overwrite performed.")
            return 1
        args.config.parent.mkdir(parents=True, exist_ok=True)
        args.config.write_text(json.dumps(Policy().model_dump(mode="json"), indent=2) + "\n")
        print(
            f"Created {args.config}; set watchlist, permissions, limits "
            "and private .env credentials."
        )
        return 0
    try:
        run_flags = (
            args.demo,
            args.doctor,
            args.once,
            args.auto,
            args.supervisor,
            args.headless,
            args.telegram_pair,
            args.session,
        )
        if (args.onboard or args.telegram_test) and any(run_flags):
            raise ValueError("Telegram setup cannot be combined with research commands")
        if args.onboard or args.telegram_test or not any(run_flags):
            from tradebot.onboarding import SetupController, test_status
            from tradebot.setup_terminal import SetupTerminal

            if not args.telegram_test and not sys.stdin.isatty():
                print("Open onboarding in an interactive terminal, or use --telegram-test.")
                return 1
            controller = SetupController(args.database)
            try:
                if args.telegram_test:
                    result = asyncio.run(controller.test())
                    print(test_status(result))
                    return 0 if result["status"] == "SENT" else 1
                SetupTerminal(controller, force=args.onboard).run()
                return 0
            finally:
                controller.close()
        policy = demo_policy() if args.demo else Policy.read(args.config)
        credentials = Credentials()
        if args.headless and not args.supervisor:
            raise ValueError("Headless mode requires --supervisor")
        if args.telegram_pair and args.demo:
            raise ValueError("Telegram pairing is not available in synthetic demo mode")
        telegram_ready = False
        if args.supervisor and not args.demo:
            from tradebot.analysis_memory import AnalysisMemory
            from tradebot.telegram import telegram_chat

            Path(".tradebot").mkdir(exist_ok=True)
            setup_store = Store(args.database or "sqlite:///.tradebot/research.db")
            try:
                memory = AnalysisMemory(setup_store)
                policy = ReportSchedule.apply(policy, memory)
                telegram_ready = bool(
                    credentials.telegram_bot_token.get_secret_value()
                    and telegram_chat(credentials, memory)
                )
            finally:
                setup_store.close()
        missing = (
            []
            if args.demo
            else (
                credentials.analysis_missing(policy, telegram=True)
                if args.supervisor
                else credentials.missing(policy)
            )
        )
        if args.supervisor and not args.demo and not telegram_ready:
            missing.append("paired Telegram chat (run tradingworkflow for onboarding)")
        if args.telegram_pair:
            missing = (
                [] if credentials.telegram_bot_token.get_secret_value() else ["telegram_bot_token"]
            )
        if args.doctor:
            print(
                json.dumps(
                    {
                        "mode": "demo" if args.demo else "research_only",
                        "orders_enabled": False,
                        "configuration_ok": not missing,
                        "missing": missing,
                        "network_access_verified": False,
                        "model_provider": policy.model_provider,
                        "model": policy.model,
                        "continuous": args.supervisor,
                        "report_interval_hours": policy.session_hours if args.supervisor else None,
                        "telegram_ready": telegram_ready if args.supervisor else None,
                    },
                    indent=2,
                )
            )
            return 1 if missing else 0
        if missing:
            doctor_command = (
                "tradingworkflow --supervisor --doctor"
                if args.supervisor
                else "tradingworkflow --doctor"
            )
            print("Configuration incomplete: " + ", ".join(missing) + f". Run {doctor_command}.")
            return 1
        directory = Path(".tradebot")
        directory.mkdir(exist_ok=True)
        url = (
            args.database or f"sqlite:///{directory / ('demo.db' if args.demo else 'research.db')}"
        )
        if args.telegram_pair:
            from tradebot.analysis_memory import AnalysisMemory
            from tradebot.telegram import TelegramNotifier

            store = Store(url)
            notifier = TelegramNotifier(credentials, AnalysisMemory(store))

            async def pair():
                try:
                    await notifier.pair()
                finally:
                    await notifier.close()
                    store.close()

            asyncio.run(pair())
            return 0
        service = TradeService(
            Store(url), policy, credentials, demo=args.demo, continuous=args.supervisor
        )
        if args.once:

            async def run_once():
                try:
                    return (
                        await service.run_analysis_cycle()
                        if args.supervisor
                        else await service.run_session()
                    )
                finally:
                    await service.close()

            result = asyncio.run(run_once())
            print(json.dumps(result, indent=2))
            return 0 if result["status"] in {"COMPLETE", "CLOSED"} else 1
        if args.headless:

            async def supervise():
                try:
                    await service.run_supervisor(print)
                finally:
                    await service.close()

            asyncio.run(supervise())
        else:
            TradingTerminal(service, automatic=args.auto).run()
        return 0
    except KeyboardInterrupt:
        print("Supervisor stopped; durable progress retained.")
        return 0
    except (ValueError, RuntimeError, OSError, TimeoutError, SQLAlchemyError) as exc:
        # Validation errors can contain input values; never print credential/config bodies.
        print(
            f"Startup/session failed ({type(exc).__name__}). Check configuration and doctor output."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
