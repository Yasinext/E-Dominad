from __future__ import annotations

import asyncio

from domainbot.config import get_settings
from domainbot.db.session import build_session_factory
from domainbot.jobs.worker import ScanJobWorker, WorkerSettings
from domainbot.rdap.client import RdapClient


def main() -> None:
    asyncio.run(_main())


async def _main() -> None:
    settings = get_settings()
    session_factory = build_session_factory(settings)
    rdap_client = RdapClient(settings)
    worker_settings = WorkerSettings.default(lease_seconds=settings.rdap_job_lease_seconds)
    try:
        await ScanJobWorker(
            session_factory=session_factory,
            rdap_checker=rdap_client,
            settings=worker_settings,
        ).run_forever()
    finally:
        await rdap_client.close()


if __name__ == "__main__":
    main()
