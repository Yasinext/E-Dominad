from __future__ import annotations

from domainbot.db.models import Watchlist


def watch_added(total_count: int, frequency: str) -> str:
    return (
        "Takip eklendi.\n"
        f"Frekans: {frequency}\n"
        f"Toplam domain: {total_count}\n"
        "Kontroller listeye yayılacak."
    )


def watch_removed() -> str:
    return "Takip durduruldu."


def watch_not_found() -> str:
    return "Takip bulunamadı."


def render_watchlists(items: list[Watchlist]) -> str:
    if not items:
        return "Aktif takip yok."
    lines = ["Aktif takipler:"]
    for index, item in enumerate(items, start=1):
        if item.single_domain:
            target = item.single_domain
        else:
            target = f"{item.root} {item.range_start}-{item.range_end}"
        lines.append(f"{index}. {target} - {item.frequency}")
    return "\n".join(lines)
