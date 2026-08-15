from __future__ import annotations

from datetime import datetime

from domainbot.reports.formatting import format_date_tr, format_datetime_tr
from domainbot.reports.types import Report


def render_text_report(report: Report, row_limit: int) -> str:
    if report.root is None:
        return _render_general_text_report(report, row_limit)

    title = "Genel rapor hazır." if report.root is None else "Rapor hazır."
    lines = [
        title,
        f"Toplam: {len(report.rows)}",
        f"Kayıtlı: {report.registered_count}",
        f"Registry kaydı bulunamadı: {report.not_found_count}",
        f"Belirsiz: {report.unknown_count}",
        f"En eski kontrol: {format_datetime_tr(report.oldest_checked_at)}",
        f"En yeni kontrol: {format_datetime_tr(report.newest_checked_at)}",
        "Kaynak: RDAP",
    ]
    if report.root is not None:
        lines.insert(1, f"Kök: {report.root}")
        lines.insert(2, f"Aralık: {report.range_start}-{report.range_end}")
        lines.insert(7, f"Son sorgu: {format_datetime_tr(report.finished_at)}")
    if len(report.rows) <= row_limit:
        lines.append("")
        for row in report.rows:
            lines.append(
                f"{row.ordinal}. {row.domain} - Alınmış: {_taken_label(row.verified_status)}"
                f" - Son geçerlilik: {format_date_tr(row.expiration_date)}"
                f" - DNS: {_dns_label(row.nameservers)}"
            )
    else:
        lines.append("Detay için excel seçeneğini kullanın.")
    return "\n".join(lines)


def _render_general_text_report(report: Report, row_limit: int) -> str:
    btk_checked = sum(1 for row in report.rows if row.btk_status is not None)
    lines = [
        "Genel rapor hazır.",
        f"Havuzdaki Domain Sayısı: {len(report.rows)}",
        f"Kayıtlı: {report.registered_count}",
        f"Registry Kaydı Bulunmayan: {report.not_found_count}",
        f"BTK kontrollü: {btk_checked}",
        f"En eski kontrol: {format_datetime_tr(report.oldest_checked_at)}",
        f"En yeni kontrol: {format_datetime_tr(report.newest_checked_at)}",
    ]
    if len(report.rows) <= row_limit:
        lines.append("")
        for row in report.rows:
            lines.append(
                f"{row.ordinal}. {row.domain} - Alınmış: {_taken_label(row.verified_status)}"
                f" - Son geçerlilik: {format_date_tr(row.expiration_date)}"
                f" - DNS: {_dns_label(row.nameservers)}"
            )
    else:
        lines.extend(["", "Detaylı rapor için excel kullanın."])
    return "\n".join(lines)


def render_expiration_report(report: Report, row_limit: int) -> str:
    lines = [
        "Geçerlilik raporu hazır.",
        f"Kök: {report.root}",
        f"Aralık: {report.range_start}-{report.range_end}",
        f"Toplam: {len(report.rows)}",
        "Kaynak: RDAP",
        "",
    ]
    visible_rows = report.rows[:row_limit]
    for row in visible_rows:
        lines.append(
            f"{row.ordinal}. {row.domain} - {_status_label(row.verified_status)}"
            f" - Bitiş: {format_date_tr(row.expiration_date)}"
        )
    if len(report.rows) > row_limit:
        lines.append("Tüm liste için excel seçeneğini kullanın.")
    return "\n".join(lines)


def _status_label(status: str | None) -> str:
    if status == "REGISTERED":
        return "Kayıtlı"
    if status == "NOT_FOUND_IN_REGISTRY":
        return "Registry kaydı bulunamadı"
    return "Belirsiz"


def _taken_label(status: str | None) -> str:
    if status == "REGISTERED":
        return "Evet"
    if status == "NOT_FOUND_IN_REGISTRY":
        return "Registry kaydı yok"
    return "Belirsiz"


def _dns_label(nameservers: tuple[str, ...]) -> str:
    return "Var" if nameservers else "Yok"


def _fmt_datetime(value: datetime | None) -> str:
    return format_datetime_tr(value)
