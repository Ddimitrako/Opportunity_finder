from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.services.market import MarketService


ATHENS = ZoneInfo("Europe/Athens")


async def run_once(service: MarketService, requested_days: int | None = None) -> None:
    status = service.refresh_status()
    days = requested_days
    if days is None and status is None:
        days = service.settings.market_initial_backfill_days
    result = await service.refresh(days)
    print(result.model_dump_json(indent=2))


async def run_interval(service: MarketService) -> None:
    while True:
        now = datetime.now(ATHENS)
        next_run = now.replace(hour=service.settings.market_refresh_hour, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        await asyncio.sleep(max(1, (next_run - now).total_seconds()))
        await run_once(service)


def main() -> None:
    parser = argparse.ArgumentParser(description="Opportunity Finder market radar refresh worker")
    parser.add_argument("--once", action="store_true", help="Run one refresh and exit")
    parser.add_argument("--interval", action="store_true", help="Run every day at MARKET_REFRESH_HOUR")
    parser.add_argument("--backfill-days", type=int, default=None, help="Override refresh lookback window")
    args = parser.parse_args()

    service = MarketService(get_settings())
    if args.once or not args.interval:
        asyncio.run(run_once(service, args.backfill_days))
    else:
        asyncio.run(run_interval(service))


if __name__ == "__main__":
    main()
