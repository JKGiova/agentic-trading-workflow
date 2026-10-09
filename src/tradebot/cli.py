"""All owner interaction is through this CLI and the single-window terminal."""

import argparse
import asyncio
import json
from pathlib import Path

from tradebot.service import TradeService, demo_policy
from tradebot.settings import Credentials, Policy
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
        policy = demo_policy() if args.demo else Policy.read(args.config)
        credentials = Credentials()
        missing = [] if args.demo else credentials.missing(policy)
        if args.doctor:
            print(
                json.dumps(
                    {
                        "mode": "demo" if args.demo else "research_only",
                        "orders_enabled": False,
                        "configuration_ok": not missing,
                        "missing": missing,
                        "network_access_verified": False,
                    },
                    indent=2,
                )
            )
            return 1 if missing else 0
        if missing:
            print("Configuration incomplete: " + ", ".join(missing) + ". Run tradebot --doctor.")
            return 1
        directory = Path(".tradebot")
        directory.mkdir(exist_ok=True)
        url = (
            args.database or f"sqlite:///{directory / ('demo.db' if args.demo else 'research.db')}"
        )
        service = TradeService(Store(url), policy, credentials, demo=args.demo)
        if args.once:

            async def run_once():
                try:
                    return await service.run_session()
                finally:
                    await service.close()

            result = asyncio.run(run_once())
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "COMPLETE" else 1
        TradingTerminal(service, automatic=args.auto).run()
        return 0
    except (ValueError, RuntimeError, OSError, TimeoutError) as exc:
        # Validation errors can contain input values; never print credential/config bodies.
        print(
            f"Startup/session failed ({type(exc).__name__}). Check configuration and doctor output."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
