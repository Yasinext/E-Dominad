from __future__ import annotations

from pathlib import Path
from typing import cast

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from domainbot.reports.formatting import format_date_tr, format_datetime_tr
from domainbot.reports.types import Report, ReportRow

HEADERS = [
    "Sıra",
    "Domain",
    "Alınmış mı",
    "Durum",
    "Son Geçerlilik Tarihi",
    "DNS Var mı",
    "Nameserverlar",
    "Registrar",
    "Kayıt Tarihi",
    "Kontrol Zamanı",
    "BTK Durumu",
    "Açıklama",
]


def write_excel_report(report: Report, path: Path) -> Path:
    workbook = Workbook()
    general_report = cast(Worksheet, workbook.active)
    general_report.title = "Genel Rapor"
    _write_general_report(general_report, report.rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)
    return path


def safe_report_filename(root: str, range_start: int, range_end: int, timestamp: str) -> str:
    safe_root = "".join(char for char in root if char.isalnum() or char == "-")[:40]
    return f"domain-report_{safe_root}_{range_start}-{range_end}_{timestamp}.xlsx"


def safe_general_report_filename(timestamp: str) -> str:
    return f"domain-report_genel_{timestamp}.xlsx"


def _write_general_report(sheet: Worksheet, rows: tuple[ReportRow, ...]) -> None:
    _write_rows(sheet, rows)


def _write_rows(sheet: Worksheet, rows: tuple[ReportRow, ...]) -> None:
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(
            [
                row.ordinal,
                _excel_text(row.domain),
                _excel_text(_taken_label(row.verified_status)),
                _excel_text(_status_label(row.verified_status)),
                _excel_text(format_date_tr(row.expiration_date)),
                _excel_text(_dns_label(row)),
                _excel_text(", ".join(row.nameservers)),
                _excel_text(row.registrar_name),
                _excel_text(format_date_tr(row.registration_date)),
                _excel_text(format_datetime_tr(row.checked_at)),
                _excel_text(_btk_label(row)),
                _excel_text(_simple_explanation(row)),
            ]
        )
    widths = [8, 32, 14, 28, 24, 12, 56, 36, 24, 28, 24, 72]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[chr(64 + index)].width = width


def _taken_label(status: str | None) -> str:
    if status == "REGISTERED":
        return "Evet"
    if status == "NOT_FOUND_IN_REGISTRY":
        return "Registry kaydı yok"
    return "Belirsiz"


def _status_label(status: str | None) -> str:
    if status == "REGISTERED":
        return "Kayıtlı"
    if status == "NOT_FOUND_IN_REGISTRY":
        return "Registry kaydı bulunamadı"
    return "Belirsiz"


def _dns_label(row: ReportRow) -> str:
    if row.nameservers:
        return "Evet"
    if row.verified_status == "REGISTERED":
        return "Hayır"
    return "-"


def _simple_explanation(row: ReportRow) -> str:
    if row.verified_status == "REGISTERED":
        if row.nameservers:
            return "Domain kayıtlı; registry tarafında nameserver bilgisi var."
        return "Domain kayıtlı; registry tarafında nameserver bilgisi görünmüyor."
    if row.verified_status == "NOT_FOUND_IN_REGISTRY":
        return "Registry kaydı bulunamadı; satın alınabilirlik ayrıca doğrulanmalıdır."
    return "Kontrol sonucu belirsiz."


def _btk_label(row: ReportRow) -> str:
    if row.btk_status is None:
        return "Bekliyor"
    if row.btk_status == "blocked":
        return "Engelli"
    if row.btk_status == "clear":
        return "Engelsiz"
    if row.btk_status == "suspect":
        return "Kontrol sürüyor"
    if row.btk_status == "inconclusive":
        return "Kontrol sürüyor"
    if row.btk_status == "dead":
        return "Kontrol sürüyor"
    if row.btk_status == "error":
        return "Kontrol sürüyor"
    return "Kontrol sürüyor"


def _excel_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text
