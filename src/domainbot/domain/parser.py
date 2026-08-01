from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from domainbot.domain.range_generator import generate_range_domains
from domainbot.domain.validation import (
    ValidationError,
    ensure_final_domain_length,
    normalize_domain,
)
from domainbot.domain.validation import normalize_root as normalize_domain_root

COMMAND_RE = re.compile(r"^/(?P<command>[a-zA-Z0-9_-]+)(?:@[A-Za-z0-9_]+)?(?:\s+(?P<args>.*))?$")
RANGE_RE = re.compile(r"^(?P<start>\d+)-(?P<end>\d+)$")


class CommandType(StrEnum):
    QUERY_SINGLE = "query_single"
    QUERY_RANGE = "query_range"
    REPORT_RANGE = "report_range"
    REPORT_GENERAL = "report_general"
    WATCH_SINGLE = "watch_single"
    WATCH_RANGE = "watch_range"
    UNWATCH_SINGLE = "unwatch_single"
    UNWATCH_RANGE = "unwatch_range"
    LIST_WATCHES = "list_watches"
    POOL_DOMAIN_REFRESH = "pool_domain_refresh"
    POOL_BTK_REFRESH = "pool_btk_refresh"


class ReportFilter(StrEnum):
    ALL = "all"
    REGISTERED = "registered"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NumericRange:
    start: int
    end: int
    width: int

    @property
    def count(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True)
class ParsedCommand:
    command_type: CommandType
    domain: str | None = None
    root: str | None = None
    numeric_range: NumericRange | None = None
    report_filter: ReportFilter = ReportFilter.ALL
    wants_excel: bool = False
    frequency: str | None = None

    def domains(self) -> tuple[str, ...]:
        if self.domain:
            return (self.domain,)
        if self.root and self.numeric_range:
            return tuple(
                generate_range_domains(
                    self.root,
                    self.numeric_range.start,
                    self.numeric_range.end,
                    self.numeric_range.width,
                )
            )
        return ()


class ParseError(ValueError):
    def __init__(self, code: str, usage: str) -> None:
        super().__init__(code)
        self.code = code
        self.usage = usage


def parse_command(
    text: str,
    max_domains: int = 100,
    max_watch_domains: int | None = None,
) -> ParsedCommand:
    match = COMMAND_RE.fullmatch(text.strip())
    if not match:
        raise ParseError("invalid_command", _valid_commands())

    command = match.group("command").lower()
    args = (match.group("args") or "").split()

    try:
        if command == "sorgu":
            return _parse_query(args, max_domains)
        if command == "rapor":
            return _parse_report(args, max_domains)
        if command == "rapor_genel":
            return _parse_general_report(args)
        if command == "takip":
            return _parse_watch(args, max_watch_domains or max_domains)
        if command == "takip_durdur":
            return _parse_unwatch(args, max_watch_domains or max_domains)
        if command == "takipler" and not args:
            return ParsedCommand(CommandType.LIST_WATCHES)
        if command == "havuz_domain_guncelle" and not args:
            return ParsedCommand(CommandType.POOL_DOMAIN_REFRESH)
        if command == "havuz_btk_guncelle" and not args:
            return ParsedCommand(CommandType.POOL_BTK_REFRESH)
    except ValidationError as exc:
        raise ParseError(exc.code, _usage_for(command)) from exc

    raise ParseError("invalid_arguments", _usage_for(command))


def _parse_query(args: list[str], max_domains: int) -> ParsedCommand:
    if len(args) == 1:
        return ParsedCommand(CommandType.QUERY_SINGLE, domain=normalize_domain(args[0]))
    if len(args) == 2:
        root = normalize_domain_root(args[0])
        numeric_range = _parse_range(args[1], max_domains)
        _validate_range_domains(root, numeric_range)
        return ParsedCommand(CommandType.QUERY_RANGE, root=root, numeric_range=numeric_range)
    raise ParseError("invalid_query", "/sorgu <domain.com> veya /sorgu <kok> <baslangic>-<bitis>")


def _parse_report(args: list[str], max_domains: int) -> ParsedCommand:
    if len(args) < 2 or len(args) > 4:
        raise ParseError("invalid_report", _usage_for("rapor"))
    root = normalize_domain_root(args[0])
    numeric_range = _parse_range(args[1], max_domains)
    report_filter = ReportFilter.ALL
    wants_excel = False
    for token in args[2:]:
        normalized = token.lower()
        if normalized == "excel":
            wants_excel = True
        elif normalized == "kayitli":
            report_filter = ReportFilter.REGISTERED
        elif normalized == "kayitsiz":
            report_filter = ReportFilter.NOT_FOUND
        elif normalized == "belirsiz":
            report_filter = ReportFilter.UNKNOWN
        else:
            raise ParseError("invalid_report_filter", _usage_for("rapor"))
    _validate_range_domains(root, numeric_range)
    return ParsedCommand(
        CommandType.REPORT_RANGE,
        root=root,
        numeric_range=numeric_range,
        report_filter=report_filter,
        wants_excel=wants_excel,
    )


def _parse_general_report(args: list[str]) -> ParsedCommand:
    if len(args) > 1:
        raise ParseError("invalid_general_report", _usage_for("rapor_genel"))
    wants_excel = False
    if args:
        if args[0].lower() != "excel":
            raise ParseError("invalid_general_report", _usage_for("rapor_genel"))
        wants_excel = True
    return ParsedCommand(CommandType.REPORT_GENERAL, wants_excel=wants_excel)


def _parse_watch(args: list[str], max_domains: int) -> ParsedCommand:
    if len(args) == 2 and args[1].lower() in {"gunluk", "haftalik"}:
        return ParsedCommand(
            CommandType.WATCH_SINGLE,
            domain=normalize_domain(args[0]),
            frequency=args[1].lower(),
        )
    if len(args) == 3 and args[2].lower() in {"gunluk", "haftalik"}:
        root = normalize_domain_root(args[0])
        numeric_range = _parse_range(args[1], max_domains)
        _validate_range_domains(root, numeric_range)
        return ParsedCommand(
            CommandType.WATCH_RANGE,
            root=root,
            numeric_range=numeric_range,
            frequency=args[2].lower(),
        )
    raise ParseError("invalid_watch", _usage_for("takip"))


def _parse_unwatch(args: list[str], max_domains: int) -> ParsedCommand:
    if len(args) == 1:
        return ParsedCommand(CommandType.UNWATCH_SINGLE, domain=normalize_domain(args[0]))
    if len(args) == 2:
        root = normalize_domain_root(args[0])
        numeric_range = _parse_range(args[1], max_domains)
        _validate_range_domains(root, numeric_range)
        return ParsedCommand(CommandType.UNWATCH_RANGE, root=root, numeric_range=numeric_range)
    raise ParseError("invalid_unwatch", _usage_for("takip_durdur"))


def _parse_range(raw: str, max_domains: int) -> NumericRange:
    match = RANGE_RE.fullmatch(raw)
    if not match:
        raise ParseError("invalid_range", "<baslangic>-<bitis>")
    start_raw = match.group("start")
    end_raw = match.group("end")
    start = int(start_raw)
    end = int(end_raw)
    if start > end:
        raise ParseError("range_start_after_end", "<baslangic>-<bitis>")
    numeric_range = NumericRange(start=start, end=end, width=len(start_raw))
    if numeric_range.count > max_domains:
        raise ParseError("too_many_domains", f"En fazla {max_domains} domain kontrol edilebilir.")
    return numeric_range


def _validate_range_domains(root: str, numeric_range: NumericRange) -> None:
    ensure_final_domain_length(root, str(numeric_range.end).zfill(numeric_range.width))


def _usage_for(command: str) -> str:
    return {
        "sorgu": "/sorgu <domain.com> veya /sorgu <kok> <baslangic>-<bitis>",
        "rapor": "/rapor <kok> <baslangic>-<bitis> [kayitli|kayitsiz|belirsiz] [excel]",
        "rapor_genel": "/rapor_genel [excel]",
        "takip": (
            "/takip <domain.com> <gunluk|haftalik> veya "
            "/takip <kok> <baslangic>-<bitis> <gunluk|haftalik>"
        ),
        "takip_durdur": "/takip_durdur <domain.com> veya /takip_durdur <kok> <baslangic>-<bitis>",
        "takipler": "/takipler",
        "havuz_domain_guncelle": "/havuz_domain_guncelle",
        "havuz_btk_guncelle": "/havuz_btk_guncelle",
    }.get(command, _valid_commands())


def _valid_commands() -> str:
    return (
        "/sorgu, /rapor, /rapor_genel, /takip, /takipler, "
        "/takip_durdur, /havuz_domain_guncelle, /havuz_btk_guncelle"
    )
