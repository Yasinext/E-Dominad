from __future__ import annotations

from collections.abc import Iterator

from domainbot.domain.validation import ensure_final_domain_length


def generate_range_domains(root: str, start: int, end: int, width: int) -> Iterator[str]:
    for value in range(start, end + 1):
        suffix = str(value).zfill(width)
        ensure_final_domain_length(root, suffix)
        yield f"{root}{suffix}.com"
