from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domainbot.domain.parser import ReportFilter


@dataclass(frozen=True)
class ReportRow:
    ordinal: int
    domain: str
    verified_status: str | None
    last_check_outcome: str | None
    registration_date: datetime | None
    expiration_date: datetime | None
    registrar_name: str | None
    registrar_iana_id: str | None
    rdap_statuses: tuple[str, ...]
    nameservers: tuple[str, ...]
    http_status: int | None
    attempt_count: int | None
    response_time_ms: int | None
    checked_at: datetime | None
    btk_status: str | None
    btk_checked_at: datetime | None
    btk_note: str | None
    btk_error: str | None
    explanation: str


@dataclass(frozen=True)
class Report:
    chat_id: int
    root: str | None
    range_start: int | None
    range_end: int | None
    job_id: str
    finished_at: datetime | None
    rows: tuple[ReportRow, ...]
    report_filter: ReportFilter

    @property
    def registered_count(self) -> int:
        return sum(1 for row in self.rows if row.verified_status == "REGISTERED")

    @property
    def not_found_count(self) -> int:
        return sum(1 for row in self.rows if row.verified_status == "NOT_FOUND_IN_REGISTRY")

    @property
    def unknown_count(self) -> int:
        return len(self.rows) - self.registered_count - self.not_found_count

    @property
    def oldest_checked_at(self) -> datetime | None:
        values = [row.checked_at for row in self.rows if row.checked_at is not None]
        return min(values) if values else None

    @property
    def newest_checked_at(self) -> datetime | None:
        values = [row.checked_at for row in self.rows if row.checked_at is not None]
        return max(values) if values else None
