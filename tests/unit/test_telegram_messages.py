from __future__ import annotations

from domainbot.domain.parser import parse_command
from domainbot.jobs.planner import build_scan_job_plan
from domainbot.telegram.messages import (
    invalid_command,
    pool_btk_refresh_started,
    pool_domain_refresh_started,
    query_accepted,
)
from domainbot.telegram.permissions import is_allowed_chat


class DummySettings:
    def __init__(self, allowed: frozenset[int]) -> None:
        self.allowed_chat_id_set = allowed


def test_query_accepted_single_domain() -> None:
    plan = build_scan_job_plan(parse_command("/sorgu example.com"))

    assert query_accepted(plan) == "Sorgu alındı.\nDomain: example.com"


def test_query_accepted_range() -> None:
    plan = build_scan_job_plan(parse_command("/sorgu marka 1-3"))

    assert query_accepted(plan) == "Sorgu alındı.\nKök: marka\nAralık: 1-3\nToplam: 3"


def test_invalid_command_message() -> None:
    assert invalid_command("/sorgu <domain.com>") == (
        "Komut geçersiz.\nKullanım: /sorgu <domain.com>"
    )


def test_pool_domain_refresh_started_message() -> None:
    assert pool_domain_refresh_started(500, 2, already_running=False) == (
        "Havuz domain güncellemesi arka planda başlatıldı.\n"
        "Domain: 500\n"
        "Parça: 2"
    )
    assert pool_domain_refresh_started(0, 1, already_running=True) == (
        "Havuz domain güncellemesi zaten arka planda çalışıyor."
    )


def test_pool_btk_refresh_started_message() -> None:
    assert pool_btk_refresh_started(500) == (
        "Havuz BTK güncellemesi arka planda başlatıldı.\nDomain: 500"
    )


def test_allowed_chat_defaults_to_allow_all_when_empty() -> None:
    assert is_allowed_chat(DummySettings(frozenset()), 123) is True  # type: ignore[arg-type]


def test_allowed_chat_filters_when_configured() -> None:
    settings = DummySettings(frozenset({123}))

    assert is_allowed_chat(settings, 123) is True  # type: ignore[arg-type]
    assert is_allowed_chat(settings, 456) is False  # type: ignore[arg-type]
