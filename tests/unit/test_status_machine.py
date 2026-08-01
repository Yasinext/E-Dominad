from __future__ import annotations

from domainbot.domain.status import DomainStatus
from domainbot.domain.status_machine import decide_transition


def test_first_verified_status_is_saved_without_change_notification() -> None:
    decision = decide_transition(None, DomainStatus.REGISTERED)

    assert decision.verified_status == DomainStatus.REGISTERED
    assert decision.changed is False
    assert decision.requires_confirmation is False


def test_transient_error_keeps_verified_status() -> None:
    decision = decide_transition(DomainStatus.REGISTERED, DomainStatus.RETRYABLE_ERROR)

    assert decision.verified_status == DomainStatus.REGISTERED
    assert decision.changed is False


def test_not_found_to_registered_changes_immediately() -> None:
    decision = decide_transition(DomainStatus.NOT_FOUND_IN_REGISTRY, DomainStatus.REGISTERED)

    assert decision.verified_status == DomainStatus.REGISTERED
    assert decision.previous_verified_status == DomainStatus.NOT_FOUND_IN_REGISTRY
    assert decision.changed is True
    assert decision.requires_confirmation is False


def test_registered_to_not_found_requires_confirmation() -> None:
    decision = decide_transition(DomainStatus.REGISTERED, DomainStatus.NOT_FOUND_IN_REGISTRY)

    assert decision.verified_status == DomainStatus.REGISTERED
    assert decision.changed is False
    assert decision.requires_confirmation is True
