from __future__ import annotations

import asyncio

from domainbot.config import get_settings
from domainbot.db.session import build_session_factory
from domainbot.watchlists.scheduler import WatchScheduler, WatchSchedulerSettings


def main() -> None:
    asyncio.run(_main())


async def _main() -> None:
    settings = get_settings()
    session_factory = build_session_factory(settings)
    await WatchScheduler(
        session_factory=session_factory,
        settings=WatchSchedulerSettings(batch_size=settings.watch_daily_batch_size),
    ).run_forever()


if __name__ == "__main__":
    main()
