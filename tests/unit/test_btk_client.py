from __future__ import annotations

import httpx
import pytest

from domainbot.btk.client import BtkClient
from domainbot.btk.types import BtkStatus
from domainbot.config import Settings


@pytest.mark.asyncio
async def test_btk_client_parses_scan_results() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/scan"
        assert request.headers["origin"] == "https://btk.example"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "domain": "blocked.com",
                        "verdict": "blocked",
                        "note": "blocked note",
                    },
                    {
                        "domain": "clear.com",
                        "verdict": "clear",
                        "note": "clear note",
                    },
                ],
                "invalid": [{"input": "bad.com", "error": "bad domain"}],
            },
        )

    client = BtkClient(Settings(btk_base_url="https://btk.example"))
    await client.client.aclose()
    client.client = httpx.AsyncClient(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
        headers={
            "Origin": client.base_url,
            "Referer": f"{client.base_url}/",
            "User-Agent": "domainbot",
        },
    )

    try:
        results = await client.scan(("blocked.com", "clear.com", "bad.com"))
    finally:
        await client.close()

    assert [result.status for result in results] == [
        BtkStatus.BLOCKED,
        BtkStatus.CLEAR,
        BtkStatus.ERROR,
    ]
    assert results[2].error == "bad domain"


@pytest.mark.asyncio
async def test_btk_client_returns_error_for_http_failure() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "failed"})

    client = BtkClient(Settings(btk_base_url="https://btk.example"))
    await client.client.aclose()
    client.client = httpx.AsyncClient(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
    )

    try:
        results = await client.scan(("example.com",))
    finally:
        await client.close()

    assert results[0].domain == "example.com"
    assert results[0].status == BtkStatus.ERROR
