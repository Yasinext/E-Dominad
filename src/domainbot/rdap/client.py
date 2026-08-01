from __future__ import annotations

import time

import httpx

from domainbot.config import Settings
from domainbot.domain.status import DomainStatus
from domainbot.rdap.result import RdapResult
from domainbot.rdap.verisign import VerisignRdapAdapter


class RdapClient:
    def __init__(self, settings: Settings, adapter: VerisignRdapAdapter | None = None) -> None:
        self.settings = settings
        self.adapter = adapter or VerisignRdapAdapter(settings.rdap_base_url)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=settings.rdap_connect_timeout_seconds,
                read=settings.rdap_read_timeout_seconds,
                write=settings.rdap_write_timeout_seconds,
                pool=settings.rdap_pool_timeout_seconds,
            ),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers=self._headers(settings),
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def check_domain(self, domain: str) -> RdapResult:
        url = self.adapter.domain_url(domain)
        attempts = max(1, self.settings.rdap_max_attempts)
        last_result: RdapResult | None = None
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                response = await self._client.get(url)
            except httpx.TimeoutException as exc:
                last_result = _transport_error(domain, attempt, "timeout", str(exc))
            except httpx.HTTPError as exc:
                last_result = _transport_error(domain, attempt, "http_error", str(exc))
            else:
                elapsed_ms = int((time.perf_counter() - started) * 1000)
                payload = _json_or_none(response)
                result = self.adapter.interpret_response(
                    domain=domain,
                    http_status=response.status_code,
                    payload=payload,
                    attempt_count=attempt,
                    response_time_ms=elapsed_ms,
                    response_url=str(response.url),
                    headers=dict(response.headers),
                )
                if result.outcome != DomainStatus.RETRYABLE_ERROR:
                    return result
                last_result = result
        if last_result is None:
            return _transport_error(domain, 0, "unknown", "No RDAP attempt was made.")
        return last_result

    @staticmethod
    def _headers(settings: Settings) -> dict[str, str]:
        headers = {"Accept": "application/rdap+json, application/json"}
        if settings.rdap_user_agent:
            headers["User-Agent"] = settings.rdap_user_agent
        return headers


def _transport_error(domain: str, attempt: int, error_type: str, message: str) -> RdapResult:
    return RdapResult(
        domain=domain,
        outcome=DomainStatus.RETRYABLE_ERROR,
        http_status=None,
        attempt_count=attempt,
        error_type=error_type,
        error_message=message,
    )


def _json_or_none(response: httpx.Response) -> dict[str, object] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict):
        return payload
    return None
