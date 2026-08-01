from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from domainbot.domain.status import DomainStatus


@dataclass(frozen=True)
class ParsedRdapDomain:
    ldh_name: str | None = None
    unicode_name: str | None = None
    handle: str | None = None
    statuses: tuple[str, ...] = ()
    registration_date: datetime | None = None
    expiration_date: datetime | None = None
    last_changed_date: datetime | None = None
    registrar_name: str | None = None
    registrar_iana_id: str | None = None
    nameservers: tuple[str, ...] = ()
    rdap_conformance: tuple[str, ...] = ()


@dataclass(frozen=True)
class RdapResult:
    domain: str
    outcome: DomainStatus
    http_status: int | None
    attempt_count: int
    response_time_ms: int | None = None
    parsed: ParsedRdapDomain | None = None
    error_type: str | None = None
    error_message: str | None = None
    response_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
