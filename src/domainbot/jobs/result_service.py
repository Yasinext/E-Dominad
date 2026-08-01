from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domainbot.domain.status import VERIFIED_STATUSES, DomainStatus
from domainbot.domain.status_machine import TransitionDecision, decide_transition
from domainbot.rdap.result import RdapResult


@dataclass(frozen=True)
class DomainUpdate:
    current_verified_status: DomainStatus | None
    previous_verified_status: DomainStatus | None
    status_changed_at: datetime | None
    last_checked_at: datetime
    last_successful_check_at: datetime | None
    last_check_outcome: DomainStatus
    consecutive_failure_count: int
    transition: TransitionDecision


def build_domain_update(
    current_verified_status: DomainStatus | None,
    consecutive_failure_count: int,
    result: RdapResult,
    checked_at: datetime,
) -> DomainUpdate:
    transition = decide_transition(current_verified_status, result.outcome)
    successful_check_at = checked_at if result.outcome in VERIFIED_STATUSES else None
    failure_count = 0 if result.outcome in VERIFIED_STATUSES else consecutive_failure_count + 1
    status_changed_at = checked_at if transition.changed else None

    return DomainUpdate(
        current_verified_status=transition.verified_status,
        previous_verified_status=transition.previous_verified_status,
        status_changed_at=status_changed_at,
        last_checked_at=checked_at,
        last_successful_check_at=successful_check_at,
        last_check_outcome=result.outcome,
        consecutive_failure_count=failure_count,
        transition=transition,
    )


def job_bucket_for_outcome(outcome: DomainStatus) -> str:
    if outcome == DomainStatus.REGISTERED:
        return "registered"
    if outcome == DomainStatus.NOT_FOUND_IN_REGISTRY:
        return "not_found"
    return "unknown"
