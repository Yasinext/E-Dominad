from __future__ import annotations

from dataclasses import dataclass

from domainbot.domain.status import TRANSIENT_OUTCOMES, VERIFIED_STATUSES, DomainStatus


@dataclass(frozen=True)
class TransitionDecision:
    verified_status: DomainStatus | None
    previous_verified_status: DomainStatus | None
    changed: bool
    requires_confirmation: bool


def decide_transition(
    current_verified_status: DomainStatus | None,
    new_outcome: DomainStatus,
) -> TransitionDecision:
    if new_outcome in TRANSIENT_OUTCOMES:
        return TransitionDecision(
            verified_status=current_verified_status,
            previous_verified_status=None,
            changed=False,
            requires_confirmation=False,
        )

    if new_outcome not in VERIFIED_STATUSES:
        return TransitionDecision(
            verified_status=current_verified_status,
            previous_verified_status=None,
            changed=False,
            requires_confirmation=False,
        )

    registered_to_not_found = (
        current_verified_status == DomainStatus.REGISTERED
        and new_outcome == DomainStatus.NOT_FOUND_IN_REGISTRY
    )
    if registered_to_not_found:
        return TransitionDecision(
            verified_status=current_verified_status,
            previous_verified_status=current_verified_status,
            changed=False,
            requires_confirmation=True,
        )

    if current_verified_status != new_outcome:
        return TransitionDecision(
            verified_status=new_outcome,
            previous_verified_status=current_verified_status,
            changed=current_verified_status is not None,
            requires_confirmation=False,
        )

    return TransitionDecision(
        verified_status=current_verified_status,
        previous_verified_status=None,
        changed=False,
        requires_confirmation=False,
    )
