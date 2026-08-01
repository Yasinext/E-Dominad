from __future__ import annotations

from enum import StrEnum


class ScanJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanJobType(StrEnum):
    SINGLE = "single"
    RANGE = "range"
    POOL_REFRESH = "pool_refresh"


class ScanJobDomainOutcome(StrEnum):
    PENDING = "PENDING"
    REGISTERED = "REGISTERED"
    NOT_FOUND_IN_REGISTRY = "NOT_FOUND_IN_REGISTRY"
    UNKNOWN = "UNKNOWN"
    RETRYABLE_ERROR = "RETRYABLE_ERROR"
    PERMANENT_ERROR = "PERMANENT_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    INVALID = "INVALID"
