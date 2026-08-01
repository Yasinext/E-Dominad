from __future__ import annotations

from domainbot.domain.parser import CommandType, ParsedCommand
from domainbot.jobs.types import ScanJobType
from domainbot.watchlists.repository import WatchPlan


def build_watch_plan(parsed: ParsedCommand) -> WatchPlan:
    frequency = parsed.frequency or "gunluk"
    is_single = (
        parsed.command_type in {CommandType.WATCH_SINGLE, CommandType.UNWATCH_SINGLE}
        and parsed.domain
    )
    if is_single:
        return WatchPlan(
            watch_type=ScanJobType.SINGLE.value,
            total_count=1,
            frequency=frequency,
            single_domain=parsed.domain,
        )
    if (
        parsed.command_type in {CommandType.WATCH_RANGE, CommandType.UNWATCH_RANGE}
        and parsed.root
        and parsed.numeric_range
    ):
        return WatchPlan(
            watch_type=ScanJobType.RANGE.value,
            total_count=parsed.numeric_range.count,
            frequency=frequency,
            root=parsed.root,
            range_start=parsed.numeric_range.start,
            range_end=parsed.numeric_range.end,
            range_width=parsed.numeric_range.width,
        )
    raise ValueError("Parsed command cannot create a watch plan.")
