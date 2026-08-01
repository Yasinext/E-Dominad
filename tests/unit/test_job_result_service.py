from __future__ import annotations

from datetime import UTC, datetime

from domainbot.domain.status import DomainStatus
from domainbot.jobs.result_service import build_domain_update, job_bucket_for_outcome
from domainbot.rdap.result import RdapResult


def test_verified_outcome_resets_failure_count() -> None:
    checked_at = datetime(2026, 7, 30, 12, tzinfo=UTC)
    update = build_domain_update(
        current_verified_status=None,
        consecutive_failure_count=3,
        result=RdapResult("example.com", DomainStatus.REGISTERED, 200, 1),
        checked_at=checked_at,
    )

    assert update.current_verified_status == DomainStatus.REGISTERED
    assert update.last_successful_check_at == checked_at
    assert update.consecutive_failure_count == 0


def test_retryable_outcome_keeps_verified_status_and_increments_failure_count() -> None:
    checked_at = datetime(2026, 7, 30, 12, tzinfo=UTC)
    update = build_domain_update(
        current_verified_status=DomainStatus.REGISTERED,
        consecutive_failure_count=1,
        result=RdapResult("example.com", DomainStatus.RETRYABLE_ERROR, None, 3),
        checked_at=checked_at,
    )

    assert update.current_verified_status == DomainStatus.REGISTERED
    assert update.last_successful_check_at is None
    assert update.consecutive_failure_count == 2


def test_status_change_records_timestamp() -> None:
    checked_at = datetime(2026, 7, 30, 12, tzinfo=UTC)
    update = build_domain_update(
        current_verified_status=DomainStatus.NOT_FOUND_IN_REGISTRY,
        consecutive_failure_count=0,
        result=RdapResult("example.com", DomainStatus.REGISTERED, 200, 1),
        checked_at=checked_at,
    )

    assert update.transition.changed is True
    assert update.status_changed_at == checked_at


def test_registered_to_not_found_needs_confirmation_without_status_change() -> None:
    checked_at = datetime(2026, 7, 30, 12, tzinfo=UTC)
    update = build_domain_update(
        current_verified_status=DomainStatus.REGISTERED,
        consecutive_failure_count=0,
        result=RdapResult("example.com", DomainStatus.NOT_FOUND_IN_REGISTRY, 404, 1),
        checked_at=checked_at,
    )

    assert update.current_verified_status == DomainStatus.REGISTERED
    assert update.transition.requires_confirmation is True
    assert update.status_changed_at is None


def test_job_bucket_counts() -> None:
    assert job_bucket_for_outcome(DomainStatus.REGISTERED) == "registered"
    assert job_bucket_for_outcome(DomainStatus.NOT_FOUND_IN_REGISTRY) == "not_found"
    assert job_bucket_for_outcome(DomainStatus.RETRYABLE_ERROR) == "unknown"
