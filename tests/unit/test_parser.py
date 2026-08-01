from __future__ import annotations

import pytest

from domainbot.domain.parser import CommandType, ParseError, ReportFilter, parse_command


def test_parse_single_domain_query() -> None:
    parsed = parse_command("/sorgu Example-1.com")

    assert parsed.command_type == CommandType.QUERY_SINGLE
    assert parsed.domain == "example-1.com"
    assert parsed.domains() == ("example-1.com",)


def test_single_domain_requires_com() -> None:
    with pytest.raises(ParseError) as exc:
        parse_command("/sorgu example")

    assert exc.value.code == "invalid_domain"


def test_parse_range_query_preserves_start_width() -> None:
    parsed = parse_command("/sorgu marka 0007-0010")

    assert parsed.command_type == CommandType.QUERY_RANGE
    assert parsed.root == "marka"
    assert parsed.numeric_range is not None
    assert parsed.numeric_range.width == 4
    assert parsed.domains() == (
        "marka0007.com",
        "marka0008.com",
        "marka0009.com",
        "marka0010.com",
    )


def test_range_limit_is_enforced() -> None:
    with pytest.raises(ParseError) as exc:
        parse_command("/sorgu marka 1-101", max_domains=100)

    assert exc.value.code == "too_many_domains"


def test_range_root_rejects_dots_and_urls() -> None:
    with pytest.raises(ParseError) as exc:
        parse_command("/sorgu example.com 1-2")

    assert exc.value.code == "invalid_root"

    with pytest.raises(ParseError):
        parse_command("/sorgu https://example 1-2")


def test_parse_report_filter_and_excel_in_any_supported_order() -> None:
    parsed = parse_command("/rapor marka 1-2 kayitsiz excel")

    assert parsed.command_type == CommandType.REPORT_RANGE
    assert parsed.report_filter == ReportFilter.NOT_FOUND
    assert parsed.wants_excel is True


def test_parse_general_report() -> None:
    parsed = parse_command("/rapor_genel")

    assert parsed.command_type == CommandType.REPORT_GENERAL
    assert parsed.wants_excel is False


def test_parse_general_excel_report() -> None:
    parsed = parse_command("/rapor_genel excel")

    assert parsed.command_type == CommandType.REPORT_GENERAL
    assert parsed.wants_excel is True


def test_parse_bot_username_suffix() -> None:
    parsed = parse_command("/sorgu@DomainMonitorBot marka 1-1")

    assert parsed.command_type == CommandType.QUERY_RANGE
    assert parsed.domains() == ("marka1.com",)


def test_parse_watch_commands() -> None:
    single = parse_command("/takip example.com gunluk")
    ranged = parse_command("/takip marka 01-02 gunluk")

    assert single.command_type == CommandType.WATCH_SINGLE
    assert single.frequency == "gunluk"
    assert ranged.command_type == CommandType.WATCH_RANGE
    assert ranged.frequency == "gunluk"
    assert ranged.domains() == ("marka01.com", "marka02.com")


def test_watch_uses_separate_limit() -> None:
    parsed = parse_command("/takip marka 1-2000 gunluk", max_domains=100, max_watch_domains=5000)

    assert parsed.command_type == CommandType.WATCH_RANGE
    assert parsed.numeric_range is not None
    assert parsed.numeric_range.count == 2000


def test_parse_unwatch_commands() -> None:
    single = parse_command("/takip_durdur example.com")
    ranged = parse_command("/takip_durdur marka 1-2")

    assert single.command_type == CommandType.UNWATCH_SINGLE
    assert ranged.command_type == CommandType.UNWATCH_RANGE


def test_removed_commands_are_rejected() -> None:
    for text in ("/yardim", "/durum", "/takip-sil example.com", "/takip-durdur example.com"):
        with pytest.raises(ParseError):
            parse_command(text)


def test_rejects_paths_ports_and_queries() -> None:
    for text in (
        "/sorgu example.com/path",
        "/sorgu example.com:443",
        "/sorgu example.com?x=1",
        "/sorgu http://example.com",
    ):
        with pytest.raises(ParseError):
            parse_command(text)
