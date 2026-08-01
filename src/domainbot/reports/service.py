from __future__ import annotations

from typing import cast

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from domainbot.db.models import Domain, DomainCheck, ScanJob, ScanJobDomain
from domainbot.domain.parser import ReportFilter
from domainbot.jobs.types import ScanJobStatus
from domainbot.reports.types import Report, ReportRow


class ReportNotFoundError(LookupError):
    pass


class ReportService:
    async def load_general_report(
        self,
        session: AsyncSession,
        chat_id: int,
        report_filter: ReportFilter,
    ) -> Report:
        statement = (
            select(Domain)
            .where(Domain.last_checked_at.is_not(None))
            .order_by(Domain.domain.asc())
        )
        domains = (await session.scalars(statement)).all()
        rows = tuple(
            row
            for row in (
                ReportRow(
                    ordinal=index,
                    domain=domain.domain,
                    verified_status=domain.current_verified_status,
                    last_check_outcome=domain.last_check_outcome,
                    registration_date=domain.registration_date,
                    expiration_date=domain.expiration_date,
                    registrar_name=domain.registrar_name,
                    registrar_iana_id=domain.registrar_iana_id,
                    rdap_statuses=_json_values(domain.rdap_statuses),
                    nameservers=_json_values(domain.nameservers),
                    http_status=None,
                    attempt_count=None,
                    response_time_ms=None,
                    checked_at=domain.last_checked_at,
                    btk_status=domain.btk_status,
                    btk_checked_at=domain.btk_checked_at,
                    btk_note=domain.btk_note,
                    btk_error=domain.btk_error,
                    explanation=_explanation(domain.last_check_outcome),
                )
                for index, domain in enumerate(domains, start=1)
            )
            if _matches_filter(row, report_filter)
        )
        return Report(
            chat_id=chat_id,
            root=None,
            range_start=None,
            range_end=None,
            job_id="general",
            finished_at=None,
            rows=rows,
            report_filter=report_filter,
        )

    async def load_range_report(
        self,
        session: AsyncSession,
        chat_id: int,
        root: str,
        range_start: int,
        range_end: int,
        report_filter: ReportFilter,
    ) -> Report:
        job = await self._latest_completed_range_job(
            session=session,
            chat_id=chat_id,
            root=root,
            range_start=range_start,
            range_end=range_end,
        )
        if job is None:
            raise ReportNotFoundError("No completed scan job found for this range.")

        rows = await self._rows_for_job(session, job.id)
        filtered_rows = tuple(row for row in rows if _matches_filter(row, report_filter))
        return Report(
            chat_id=chat_id,
            root=root,
            range_start=range_start,
            range_end=range_end,
            job_id=str(job.id),
            finished_at=job.finished_at,
            rows=filtered_rows,
            report_filter=report_filter,
        )

    async def _latest_completed_range_job(
        self,
        session: AsyncSession,
        chat_id: int,
        root: str,
        range_start: int,
        range_end: int,
    ) -> ScanJob | None:
        statement = (
            select(ScanJob)
            .where(
                ScanJob.chat_id == chat_id,
                ScanJob.root == root,
                ScanJob.range_start == range_start,
                ScanJob.range_end == range_end,
                ScanJob.status == ScanJobStatus.COMPLETED.value,
            )
            .order_by(ScanJob.finished_at.desc().nullslast(), ScanJob.created_at.desc())
            .limit(1)
        )
        return cast(ScanJob | None, await session.scalar(statement))

    async def _rows_for_job(self, session: AsyncSession, job_id: object) -> tuple[ReportRow, ...]:
        latest_check = (
            select(
                DomainCheck.domain_id.label("domain_id"),
                DomainCheck.scan_job_id.label("scan_job_id"),
                DomainCheck.http_status.label("http_status"),
                DomainCheck.attempt_count.label("attempt_count"),
                DomainCheck.response_time_ms.label("response_time_ms"),
            )
            .where(DomainCheck.scan_job_id == job_id)
            .subquery()
        )
        statement: Select[tuple[ScanJobDomain, Domain, object, object, object]] = (
            select(
                ScanJobDomain,
                Domain,
                latest_check.c.http_status,
                latest_check.c.attempt_count,
                latest_check.c.response_time_ms,
            )
            .join(Domain, Domain.id == ScanJobDomain.domain_id)
            .outerjoin(
                latest_check,
                (latest_check.c.domain_id == Domain.id)
                & (latest_check.c.scan_job_id == ScanJobDomain.scan_job_id),
            )
            .where(ScanJobDomain.scan_job_id == job_id)
            .order_by(ScanJobDomain.ordinal.asc())
        )
        rows = (await session.execute(statement)).all()
        return tuple(
            ReportRow(
                ordinal=scan_row.ordinal,
                domain=domain.domain,
                verified_status=scan_row.verified_status,
                last_check_outcome=scan_row.outcome,
                registration_date=domain.registration_date,
                expiration_date=domain.expiration_date,
                registrar_name=domain.registrar_name,
                registrar_iana_id=domain.registrar_iana_id,
                rdap_statuses=_json_values(domain.rdap_statuses),
                nameservers=_json_values(domain.nameservers),
                http_status=http_status,
                attempt_count=attempt_count,
                response_time_ms=response_time_ms,
                checked_at=scan_row.checked_at,
                btk_status=domain.btk_status,
                btk_checked_at=domain.btk_checked_at,
                btk_note=domain.btk_note,
                btk_error=domain.btk_error,
                explanation=_explanation(scan_row.outcome),
            )
            for scan_row, domain, http_status, attempt_count, response_time_ms in rows
        )


def _matches_filter(row: ReportRow, report_filter: ReportFilter) -> bool:
    if report_filter == ReportFilter.ALL:
        return True
    if report_filter == ReportFilter.REGISTERED:
        return row.verified_status == "REGISTERED"
    if report_filter == ReportFilter.NOT_FOUND:
        return row.verified_status == "NOT_FOUND_IN_REGISTRY"
    if report_filter == ReportFilter.UNKNOWN:
        return row.verified_status not in {"REGISTERED", "NOT_FOUND_IN_REGISTRY"}
    return True


def _json_values(value: dict[str, object] | None) -> tuple[str, ...]:
    if not value:
        return ()
    raw_values = value.get("values")
    if not isinstance(raw_values, list):
        return ()
    return tuple(str(item) for item in raw_values if item is not None)


def _explanation(outcome: str | None) -> str:
    if outcome == "REGISTERED":
        return "RDAP kaydı bulundu."
    if outcome == "NOT_FOUND_IN_REGISTRY":
        return "Registry kaydı bulunamadı; satın alınabilirlik registrar ile doğrulanmadı."
    if outcome in {"RETRYABLE_ERROR", "PARSE_ERROR"}:
        return "Geçici veya ayrıştırma hatası; doğrulanmış durum değiştirilmedi."
    return "Belirsiz."
