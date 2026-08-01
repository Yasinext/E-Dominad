from __future__ import annotations

import asyncio
import time

from sqlalchemy import func, select

from domainbot.config import get_settings
from domainbot.db.models import Domain, DomainCheck, ScanJob, TelegramOutbox
from domainbot.db.session import build_session_factory
from domainbot.domain.parser import parse_command
from domainbot.domain.status import DomainStatus
from domainbot.jobs.service import ScanJobService
from domainbot.jobs.worker import ScanJobWorker, WorkerSettings
from domainbot.rdap.result import RdapResult

SMOKE_CHAT_ID = -1001234567890


class FakeRdapChecker:
    async def check_domain(self, domain: str) -> RdapResult:
        return RdapResult(
            domain=domain,
            outcome=DomainStatus.NOT_FOUND_IN_REGISTRY,
            http_status=404,
            attempt_count=1,
            response_time_ms=12,
        )


async def main() -> None:
    settings = get_settings()
    session_factory = build_session_factory(settings)
    domain = f"codexsmoke{int(time.time())}.com"
    parsed = parse_command(f"/sorgu {domain}", max_domains=settings.max_domains_per_command)

    async with session_factory() as session:
        async with session.begin():
            job = await ScanJobService().create_from_command(
                session=session,
                parsed=parsed,
                chat_id=SMOKE_CHAT_ID,
                requested_by=1,
            )
            job_id = job.id

    worker = ScanJobWorker(
        session_factory=session_factory,
        rdap_checker=FakeRdapChecker(),
        settings=WorkerSettings(worker_id="local-smoke", idle_sleep_seconds=0.1),
    )
    did_work = await worker.run_once()

    async with session_factory() as session:
        job = await session.get(ScanJob, job_id)
        outbox = await session.scalar(
            select(TelegramOutbox).where(
                TelegramOutbox.idempotency_key == f"scan_completed:{job_id}"
            )
        )

    if not did_work or job is None or outbox is None:
        raise SystemExit("Smoke test failed.")
    print(
        "Smoke OK:",
        f"job={job.status}",
        f"completed={job.completed_count}/{job.total_count}",
        f"outbox={outbox.status}",
    )

    async with session_factory() as session:
        async with session.begin():
            parsed_again = parse_command(
                f"/sorgu {domain}",
                max_domains=settings.max_domains_per_command,
            )
            second_job = await ScanJobService().create_from_command(
                session=session,
                parsed=parsed_again,
                chat_id=SMOKE_CHAT_ID,
                requested_by=1,
            )
            second_job_id = second_job.id

    await worker.run_once()

    async with session_factory() as session:
        domain_count = await session.scalar(
            select(func.count()).select_from(Domain).where(Domain.domain == domain)
        )
        check_count = await session.scalar(
            select(func.count())
            .select_from(DomainCheck)
            .join(Domain, Domain.id == DomainCheck.domain_id)
            .where(Domain.domain == domain)
        )
        second_job = await session.get(ScanJob, second_job_id)

    if int(domain_count or 0) != 1 or int(check_count or 0) != 2 or second_job is None:
        raise SystemExit("Repeat-domain smoke test failed.")
    print("Repeat OK:", f"domain_rows={domain_count}", f"check_rows={check_count}")


if __name__ == "__main__":
    asyncio.run(main())
