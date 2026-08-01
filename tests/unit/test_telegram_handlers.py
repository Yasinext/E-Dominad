from __future__ import annotations

import pytest

from domainbot.telegram.handlers import handle_message

ALLOWED_TEST_CHAT_ID = -1001234567890


class DummyChat:
    def __init__(self, chat_id: int, chat_type: str) -> None:
        self.id = chat_id
        self.type = chat_type


class DummyMessage:
    def __init__(self, text: str, chat: DummyChat) -> None:
        self.text = text
        self.chat = chat
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


class DummySettings:
    max_domains_per_command = 100
    allowed_chat_id_set = frozenset({ALLOWED_TEST_CHAT_ID})


@pytest.mark.asyncio
async def test_private_chat_commands_are_ignored() -> None:
    message = DummyMessage("/sorgu example.com", DummyChat(123, "private"))

    await handle_message(
        message,  # type: ignore[arg-type]
        DummySettings(),  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
    )

    assert message.answers == []


@pytest.mark.asyncio
async def test_unauthorized_group_gets_short_rejection() -> None:
    message = DummyMessage("/sorgu example.com", DummyChat(-1, "group"))

    await handle_message(
        message,  # type: ignore[arg-type]
        DummySettings(),  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
    )

    assert message.answers == ["Bu bot yalnızca yetkili Telegram gruplarında çalışır."]
