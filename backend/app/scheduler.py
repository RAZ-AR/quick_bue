"""Scheduler process: `python -m app.scheduler`. One tick per minute.

Planned jobs (docs/02-mvp.md §8): expire negotiations past expires_at, auto-accept deliveries after 48 h,
remind about contract prices that end in 3 days. The tick is a no-op until those modules exist.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

log = logging.getLogger("qb.scheduler")


async def tick() -> None:
    log.debug("tick")


async def main() -> None:
    scheduler = AsyncIOScheduler(timezone="UTC")
    # max_instances=1 + coalesce: a slow tick never overlaps the next one
    scheduler.add_job(tick, "cron", second=5, max_instances=1, coalesce=True)
    scheduler.start()
    log.info("scheduler started")
    await asyncio.Event().wait()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
