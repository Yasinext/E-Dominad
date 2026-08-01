from __future__ import annotations

from dataclasses import dataclass

from domainbot.domain.parser import CommandType, ParsedCommand
from domainbot.jobs.types import ScanJobType


@dataclass(frozen=True)
class ScanJobPlan:
    job_type: ScanJobType
    domains: tuple[str, ...]
    root: str | None = None
    range_start: int | None = None
    range_end: int | None = None
    range_width: int | None = None
    single_domain: str | None = None

    @property
    def total_count(self) -> int:
        return len(self.domains)


def build_scan_job_plan(parsed: ParsedCommand) -> ScanJobPlan:
    if parsed.command_type == CommandType.QUERY_SINGLE and parsed.domain:
        return ScanJobPlan(
            job_type=ScanJobType.SINGLE,
            domains=(parsed.domain,),
            single_domain=parsed.domain,
        )
    if parsed.command_type == CommandType.QUERY_RANGE and parsed.root and parsed.numeric_range:
        return ScanJobPlan(
            job_type=ScanJobType.RANGE,
            domains=parsed.domains(),
            root=parsed.root,
            range_start=parsed.numeric_range.start,
            range_end=parsed.numeric_range.end,
            range_width=parsed.numeric_range.width,
        )
    raise ValueError("Parsed command cannot create a scan job.")
