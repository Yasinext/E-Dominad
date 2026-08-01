from __future__ import annotations

import pytest

from domainbot.domain.parser import parse_command
from domainbot.jobs.planner import build_scan_job_plan
from domainbot.jobs.types import ScanJobType


def test_build_single_job_plan() -> None:
    plan = build_scan_job_plan(parse_command("/sorgu example.com"))

    assert plan.job_type == ScanJobType.SINGLE
    assert plan.single_domain == "example.com"
    assert plan.domains == ("example.com",)
    assert plan.total_count == 1


def test_build_range_job_plan_preserves_width() -> None:
    plan = build_scan_job_plan(parse_command("/sorgu marka 007-009"))

    assert plan.job_type == ScanJobType.RANGE
    assert plan.root == "marka"
    assert plan.range_start == 7
    assert plan.range_end == 9
    assert plan.range_width == 3
    assert plan.domains == ("marka007.com", "marka008.com", "marka009.com")


def test_rejects_non_scan_commands() -> None:
    with pytest.raises(ValueError):
        build_scan_job_plan(parse_command("/rapor_genel"))
    with pytest.raises(ValueError):
        build_scan_job_plan(parse_command("/havuz_domain_guncelle"))
