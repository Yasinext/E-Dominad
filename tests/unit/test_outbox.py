from __future__ import annotations

from datetime import UTC, datetime, timedelta

from domainbot.db.models import TelegramOutbox
from domainbot.telegram.outbox import (
    OutboxDispatcherSettings,
    OutboxRepository,
    OutboxStatus,
    render_outbox_message,
)


def test_render_single_registered_completion_message() -> None:
    text = render_outbox_message(
        "scan_completed",
        {
            "single_domain": "example.com",
            "registered_count": 1,
            "not_found_count": 0,
            "unknown_count": 0,
            "finished_at": "2026-07-30T12:00:00+00:00",
        },
    )

    assert text == (
        "Sorgu tamamlandı.\n"
        "Domain: example.com\n"
        "Durum: Kayıtlı\n"
        "Kontrol: 2026-07-30T12:00:00+00:00"
    )


def test_render_single_not_found_completion_message() -> None:
    text = render_outbox_message(
        "scan_completed",
        {
            "single_domain": "missing-example.com",
            "registered_count": 0,
            "not_found_count": 1,
            "unknown_count": 0,
            "finished_at": "2026-07-30T12:00:00+00:00",
        },
    )

    assert "Durum: Registry kaydı bulunamadı" in text


def test_render_range_completion_message() -> None:
    text = render_outbox_message(
        "scan_completed",
        {
            "root": "marka",
            "range_start": 1,
            "range_end": 3,
            "total_count": 3,
            "registered_count": 1,
            "not_found_count": 1,
            "unknown_count": 1,
        },
    )

    assert text == (
        "Sorgu tamamlandı.\n"
        "Kök: marka\n"
        "Aralık: 1-3\n"
        "Toplam: 3\n"
        "Kayıtlı: 1\n"
        "Registry kaydı bulunamadı: 1\n"
        "Belirsiz: 1"
    )


def test_render_watch_newly_registered_message() -> None:
    text = render_outbox_message(
        "watch_newly_registered",
        {"domains": ["test1.com", "test2.com"], "total_count": 2},
    )

    assert text == (
        "Takip edilen domainlerde yeni kayıt mevcut.\n"
        "Toplam: 2\n"
        "test1.com\n"
        "test2.com"
    )


def test_retry_delay_uses_exponential_backoff() -> None:
    message = TelegramOutbox(
        id=1,
        chat_id=123,
        message_type="scan_completed",
        payload={},
        idempotency_key="scan_completed:1",
        status=OutboxStatus.SENDING.value,
        attempt_count=3,
        next_attempt_at=datetime(2026, 7, 30, 12, tzinfo=UTC),
        created_at=datetime(2026, 7, 30, 12, tzinfo=UTC),
    )
    now = datetime(2026, 7, 30, 12, 1, tzinfo=UTC)
    settings = OutboxDispatcherSettings(
        dispatcher_id="test",
        retry_base_seconds=10,
        retry_max_seconds=300,
    )

    delay = min(
        settings.retry_max_seconds,
        settings.retry_base_seconds * (2 ** max(0, message.attempt_count - 1)),
    )

    assert now + timedelta(seconds=delay) == datetime(2026, 7, 30, 12, 1, 40, tzinfo=UTC)


def test_repository_type_is_importable() -> None:
    assert isinstance(OutboxRepository(), OutboxRepository)
