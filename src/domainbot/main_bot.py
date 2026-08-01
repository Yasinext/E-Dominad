from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from domainbot.config import get_settings
from domainbot.db.session import build_session_factory
from domainbot.telegram.handlers import create_router
from domainbot.telegram.outbox import AiogramSender, OutboxDispatcher


def main() -> None:
    asyncio.run(_main())


async def _main() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required.")

    bot = Bot(token=settings.telegram_bot_token)
    session_factory = build_session_factory(settings)
    dispatcher = Dispatcher(settings=settings, session_factory=session_factory)
    dispatcher.include_router(create_router())
    outbox_task = asyncio.create_task(
        OutboxDispatcher(session_factory=session_factory, sender=AiogramSender(bot)).run_forever()
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        outbox_task.cancel()


if __name__ == "__main__":
    main()
