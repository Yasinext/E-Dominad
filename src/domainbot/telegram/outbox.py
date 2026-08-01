from __future__ import annotations

import asyncio
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Protocol

from aiogram import Bot
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domainbot.db.models import TelegramOutbox


class OutboxStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class TelegramSender(Protocol):
    async def send_message(self, chat_id: int, text: str) -> object: ...


@dataclass(frozen=True)
class OutboxDispatcherSettings:
    dispatcher_id: str
    lease_seconds: int = 120
    idle_sleep_seconds: float = 2.0
    retry_base_seconds: int = 10
    retry_max_seconds: int = 300

    @classmethod
    def default(cls) -> OutboxDispatcherSettings:
        return cls(dispatcher_id=f"{socket.gethostname()}:domainbot-outbox")


class AiogramSender:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def send_message(self, chat_id: int, text: str) -> object:
        return await self.bot.send_message(chat_id=chat_id, text=text)


class OutboxRepository:
    async def claim_next(
        self,
        session: AsyncSession,
        dispatcher_id: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> TelegramOutbox | None:
        claimed_at = now or datetime.now(UTC)
        stale_sending = (
            (TelegramOutbox.status == OutboxStatus.SENDING.value)
            & (TelegramOutbox.locked_at.is_not(None))
            & (TelegramOutbox.locked_at < claimed_at - timedelta(seconds=lease_seconds))
        )
        due_pending = (
            (TelegramOutbox.status == OutboxStatus.PENDING.value)
            & (TelegramOutbox.next_attempt_at <= claimed_at)
        )
        statement: Select[tuple[TelegramOutbox]] = (
            select(TelegramOutbox)
            .where(due_pending | stale_sending)
            .order_by(TelegramOutbox.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        message = await session.scalar(statement)
        if message is None:
            return None

        message.status = OutboxStatus.SENDING.value
        message.locked_by = dispatcher_id
        message.locked_at = claimed_at
        message.attempt_count += 1
        return message

    async def mark_sent(
        self,
        session: AsyncSession,
        message_id: int,
        now: datetime | None = None,
    ) -> None:
        message = await session.get(TelegramOutbox, message_id)
        if message is None:
            return
        sent_at = now or datetime.now(UTC)
        message.status = OutboxStatus.SENT.value
        message.sent_at = sent_at
        message.locked_by = None
        message.locked_at = None

    async def mark_retry(
        self,
        session: AsyncSession,
        message_id: int,
        settings: OutboxDispatcherSettings,
        now: datetime | None = None,
    ) -> None:
        message = await session.get(TelegramOutbox, message_id)
        if message is None:
            return
        failed_at = now or datetime.now(UTC)
        delay_seconds = min(
            settings.retry_max_seconds,
            settings.retry_base_seconds * (2 ** max(0, message.attempt_count - 1)),
        )
        message.status = OutboxStatus.PENDING.value
        message.next_attempt_at = failed_at + timedelta(seconds=delay_seconds)
        message.locked_by = None
        message.locked_at = None


class OutboxDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        sender: TelegramSender,
        repository: OutboxRepository | None = None,
        settings: OutboxDispatcherSettings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.sender = sender
        self.repository = repository or OutboxRepository()
        self.settings = settings or OutboxDispatcherSettings.default()

    async def run_once(self) -> bool:
        async with self.session_factory() as session:
            async with session.begin():
                message = await self.repository.claim_next(
                    session,
                    dispatcher_id=self.settings.dispatcher_id,
                    lease_seconds=self.settings.lease_seconds,
                )
                if message is None:
                    return False
                message_id = message.id
                chat_id = message.chat_id
                text = render_outbox_message(message.message_type, message.payload)

        try:
            await self.sender.send_message(chat_id=chat_id, text=text)
        except Exception:
            async with self.session_factory() as session:
                async with session.begin():
                    await self.repository.mark_retry(session, message_id, self.settings)
            return True

        async with self.session_factory() as session:
            async with session.begin():
                await self.repository.mark_sent(session, message_id)
        return True

    async def run_forever(self) -> None:
        while True:
            did_work = await self.run_once()
            if not did_work:
                await asyncio.sleep(self.settings.idle_sleep_seconds)


def render_outbox_message(message_type: str, payload: Mapping[str, object]) -> str:
    if message_type == "scan_completed":
        return _render_scan_completed(payload)
    if message_type == "watch_newly_registered":
        return _render_watch_newly_registered(payload)
    return "Bildirim hazır."


def _render_scan_completed(payload: Mapping[str, object]) -> str:
    single_domain = _text_or_none(payload.get("single_domain"))
    if single_domain:
        return (
            "Sorgu tamamlandı.\n"
            f"Domain: {single_domain}\n"
            f"Durum: {_single_status(payload)}\n"
            f"Kontrol: {_text(payload.get('finished_at'))}"
        )
    return (
        "Sorgu tamamlandı.\n"
        f"Kök: {_text(payload.get('root'))}\n"
        f"Aralık: {_text(payload.get('range_start'))}-{_text(payload.get('range_end'))}\n"
        f"Toplam: {_text(payload.get('total_count'))}\n"
        f"Kayıtlı: {_text(payload.get('registered_count'))}\n"
        f"Registry kaydı bulunamadı: {_text(payload.get('not_found_count'))}\n"
        f"Belirsiz: {_text(payload.get('unknown_count'))}"
    )


def _render_watch_newly_registered(payload: Mapping[str, object]) -> str:
    domains = payload.get("domains")
    domain_list = [str(item) for item in domains] if isinstance(domains, list) else []
    lines = [
        "Takip edilen domainlerde yeni kayıt var.",
        f"Toplam: {_text(payload.get('total_count'))}",
    ]
    lines.extend(domain_list[:20])
    if len(domain_list) > 20:
        lines.append("Detay için genel raporu kullanın.")
    return "\n".join(lines)


def _single_status(payload: Mapping[str, object]) -> str:
    if _int(payload.get("registered_count")) == 1:
        return "Kayıtlı"
    if _int(payload.get("not_found_count")) == 1:
        return "Registry kaydı bulunamadı"
    return "Belirsiz"


def _text(value: object) -> str:
    if value is None:
        return "-"
    return str(value)


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
