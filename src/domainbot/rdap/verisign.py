from __future__ import annotations

from urllib.parse import quote

from domainbot.domain.status import DomainStatus
from domainbot.rdap.parser import RdapParseError, parse_domain_response
from domainbot.rdap.result import RdapResult


class VerisignRdapAdapter:
    def __init__(self, base_url: str = "https://rdap.verisign.com/com/v1") -> None:
        self.base_url = base_url.rstrip("/")

    def domain_url(self, domain: str) -> str:
        return f"{self.base_url}/domain/{quote(domain, safe='')}"

    def interpret_response(
        self,
        domain: str,
        http_status: int,
        payload: dict[str, object] | None,
        attempt_count: int,
        response_time_ms: int | None = None,
        response_url: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> RdapResult:
        if http_status == 200:
            if payload is None:
                return self._parse_error(domain, http_status, attempt_count, response_time_ms)
            try:
                parsed = parse_domain_response(payload)
            except RdapParseError as exc:
                return self._parse_error(
                    domain, http_status, attempt_count, response_time_ms, str(exc)
                )
            return RdapResult(
                domain=domain,
                outcome=DomainStatus.REGISTERED,
                http_status=http_status,
                attempt_count=attempt_count,
                response_time_ms=response_time_ms,
                parsed=parsed,
                response_url=response_url,
                headers=headers or {},
            )
        if http_status == 404:
            return RdapResult(
                domain=domain,
                outcome=DomainStatus.NOT_FOUND_IN_REGISTRY,
                http_status=http_status,
                attempt_count=attempt_count,
                response_time_ms=response_time_ms,
                response_url=response_url,
                headers=headers or {},
            )
        if http_status == 400:
            outcome = DomainStatus.INVALID
        elif http_status == 429 or 500 <= http_status <= 599:
            outcome = DomainStatus.RETRYABLE_ERROR
        elif 400 <= http_status <= 499:
            outcome = DomainStatus.PERMANENT_ERROR
        else:
            outcome = DomainStatus.UNKNOWN

        return RdapResult(
            domain=domain,
            outcome=outcome,
            http_status=http_status,
            attempt_count=attempt_count,
            response_time_ms=response_time_ms,
            response_url=response_url,
            headers=headers or {},
        )

    @staticmethod
    def _parse_error(
        domain: str,
        http_status: int,
        attempt_count: int,
        response_time_ms: int | None,
        message: str = "Unexpected RDAP JSON.",
    ) -> RdapResult:
        return RdapResult(
            domain=domain,
            outcome=DomainStatus.PARSE_ERROR,
            http_status=http_status,
            attempt_count=attempt_count,
            response_time_ms=response_time_ms,
            error_type="parse_error",
            error_message=message,
        )
