from __future__ import annotations

from collections.abc import Sequence

import httpx

from domainbot.btk.types import BtkResult, BtkStatus
from domainbot.config import Settings


class BtkClient:
    def __init__(self, settings: Settings) -> None:
        timeout = httpx.Timeout(
            connect=settings.btk_connect_timeout_seconds,
            read=settings.btk_read_timeout_seconds,
            write=settings.btk_write_timeout_seconds,
            pool=settings.btk_pool_timeout_seconds,
        )
        self.base_url = settings.btk_base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={
                "Origin": self.base_url,
                "Referer": f"{self.base_url}/",
                "User-Agent": settings.btk_user_agent or settings.app_name,
            },
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def scan(self, domains: Sequence[str]) -> tuple[BtkResult, ...]:
        if not domains:
            return ()
        try:
            response = await self.client.post(
                "/scan",
                json={"domains": "\n".join(domains)},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return tuple(_error_result(domain, str(exc)) for domain in domains)

        if not isinstance(payload, dict):
            return tuple(
                _error_result(domain, "BTK cevabı beklenen JSON formatında değil.")
                for domain in domains
            )

        results_by_domain: dict[str, BtkResult] = {}
        raw_results = payload.get("results", [])
        if isinstance(raw_results, list):
            for item in raw_results:
                result = _parse_result(item)
                if result is not None:
                    results_by_domain[result.domain] = result

        raw_invalid = payload.get("invalid", [])
        if isinstance(raw_invalid, list):
            for item in raw_invalid:
                result = _parse_invalid(item)
                if result is not None:
                    results_by_domain[result.domain] = result

        return tuple(
            results_by_domain.get(domain, _error_result(domain, "BTK cevabında sonuç bulunamadı."))
            for domain in domains
        )


def _parse_result(item: object) -> BtkResult | None:
    if not isinstance(item, dict):
        return None
    raw_domain = item.get("domain")
    raw_verdict = item.get("verdict")
    if not isinstance(raw_domain, str) or not isinstance(raw_verdict, str):
        return None
    try:
        status = BtkStatus(raw_verdict)
    except ValueError:
        status = BtkStatus.ERROR
    note = item.get("note")
    return BtkResult(
        domain=raw_domain,
        status=status,
        note=note if isinstance(note, str) else None,
        error=None if status != BtkStatus.ERROR else "BTK sonucu hata döndü.",
    )


def _parse_invalid(item: object) -> BtkResult | None:
    if not isinstance(item, dict):
        return None
    raw_domain = item.get("input")
    if not isinstance(raw_domain, str):
        return None
    raw_error = item.get("error")
    error = raw_error if isinstance(raw_error, str) else "Geçersiz domain."
    return _error_result(raw_domain, error)


def _error_result(domain: str, error: str) -> BtkResult:
    return BtkResult(domain=domain, status=BtkStatus.ERROR, error=error[:500])
