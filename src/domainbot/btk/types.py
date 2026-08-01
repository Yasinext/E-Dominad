from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BtkStatus(StrEnum):
    BLOCKED = "blocked"
    CLEAR = "clear"
    SUSPECT = "suspect"
    INCONCLUSIVE = "inconclusive"
    DEAD = "dead"
    ERROR = "error"


@dataclass(frozen=True)
class BtkResult:
    domain: str
    status: BtkStatus
    note: str | None = None
    error: str | None = None
