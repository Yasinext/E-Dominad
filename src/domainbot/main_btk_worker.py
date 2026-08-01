from __future__ import annotations

import asyncio

from domainbot.btk.client import BtkClient
from domainbot.btk.worker import BtkWorker, BtkWorkerSettings
from domainbot.config import get_settings
from domainbot.db.session import build_session_factory


def main() -> None:
    asyncio.run(_main())


async def _main() -> None:
    settings = get_settings()
    session_factory = build_session_factory(settings)
    client = BtkClient(settings)
    worker_settings = BtkWorkerSettings.default(
        batch_size=settings.btk_batch_size,
        idle_sleep_seconds=settings.btk_idle_sleep_seconds,
        batch_sleep_seconds=settings.btk_batch_sleep_seconds,
        retry_interval_seconds=settings.btk_retry_interval_seconds,
    )
    try:
        await BtkWorker(
            session_factory=session_factory,
            scanner=client,
            settings=worker_settings,
        ).run_forever()
    finally:
        await client.close()


if __name__ == "__main__":
    main()
