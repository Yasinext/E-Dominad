from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domainbot.watchlists.repository import WatchlistRepository


@dataclass(frozen=True)
class WatchSchedulerSettings:
    batch_size: int
    due_limit: int = 10
    idle_sleep_seconds: float = 60.0


class WatchScheduler:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        repository: WatchlistRepository | None = None,
        settings: WatchSchedulerSettings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.repository = repository or WatchlistRepository()
        self.settings = settings or WatchSchedulerSettings(batch_size=300)

    async def run_once(self) -> int:
        async with self.session_factory() as session:
            async with session.begin():
                watchlists = await self.repository.claim_due_watchlists(
                    session,
                    limit=self.settings.due_limit,
                )
                for watchlist in watchlists:
                    await self.repository.create_due_scan_job(
                        session,
                        watchlist,
                        batch_size=self.settings.batch_size,
                    )
                return len(watchlists)

    async def run_forever(self) -> None:
        while True:
            count = await self.run_once()
            if count == 0:
                await asyncio.sleep(self.settings.idle_sleep_seconds)
