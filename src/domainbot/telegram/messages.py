from __future__ import annotations

from domainbot.jobs.planner import ScanJobPlan


def unauthorized_group() -> str:
    return "Bu bot yalnızca yetkili Telegram gruplarında çalışır."


def invalid_command(usage: str) -> str:
    return f"Komut geçersiz.\nKullanım: {usage}"


def command_not_ready() -> str:
    return "Komut geçici olarak hazır değil."


def report_not_found() -> str:
    return "Rapor bulunamadı.\nÖnce aynı kök ve aralık için /sorgu çalıştırın."


def query_accepted(plan: ScanJobPlan) -> str:
    if plan.single_domain:
        return f"Sorgu alındı.\nDomain: {plan.single_domain}"
    return (
        "Sorgu alındı.\n"
        f"Kök: {plan.root}\n"
        f"Aralık: {plan.range_start}-{plan.range_end}\n"
        f"Toplam: {plan.total_count}"
    )
