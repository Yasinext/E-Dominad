from __future__ import annotations

from aiogram.types import Chat

from domainbot.config import Settings

GROUP_CHAT_TYPES = frozenset({"group", "supergroup"})


def is_group_chat(chat: Chat) -> bool:
    return chat.type in GROUP_CHAT_TYPES


def is_allowed_chat(settings: Settings, chat_id: int) -> bool:
    allowed = settings.allowed_chat_id_set
    return not allowed or chat_id in allowed
