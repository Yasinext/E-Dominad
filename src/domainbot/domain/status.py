from __future__ import annotations

from enum import StrEnum


class DomainStatus(StrEnum):
    REGISTERED = "REGISTERED"
    NOT_FOUND_IN_REGISTRY = "NOT_FOUND_IN_REGISTRY"
    AVAILABLE_CONFIRMED = "AVAILABLE_CONFIRMED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"
    RETRYABLE_ERROR = "RETRYABLE_ERROR"
    PERMANENT_ERROR = "PERMANENT_ERROR"
    PARSE_ERROR = "PARSE_ERROR"


VERIFIED_STATUSES = frozenset(
    {
        DomainStatus.REGISTERED,
        DomainStatus.NOT_FOUND_IN_REGISTRY,
        DomainStatus.AVAILABLE_CONFIRMED,
    }
)

TRANSIENT_OUTCOMES = frozenset({DomainStatus.RETRYABLE_ERROR, DomainStatus.PARSE_ERROR})
