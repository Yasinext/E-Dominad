from __future__ import annotations

from datetime import UTC, datetime

from aiogram import Router
from aiogram.types import FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from domainbot.config import Settings
from domainbot.domain.parser import CommandType, ParseError, parse_command
from domainbot.jobs.planner import build_scan_job_plan
from domainbot.jobs.service import ScanJobService
from domainbot.pool.service import PoolRefreshService
from domainbot.reports.excel import (
    safe_general_report_filename,
    safe_report_filename,
    write_excel_report,
)
from domainbot.reports.service import ReportNotFoundError, ReportService
from domainbot.reports.text import render_text_report
from domainbot.telegram.messages import (
    command_not_ready,
    invalid_command,
    pool_btk_refresh_started,
    pool_delete_completed,
    pool_domain_refresh_started,
    query_accepted,
    report_not_found,
    unauthorized_group,
)
from domainbot.telegram.permissions import is_allowed_chat, is_group_chat
from domainbot.watchlists.messages import (
    render_watchlists,
    watch_added,
    watch_not_found,
    watch_removed,
)
from domainbot.watchlists.repository import WatchlistRepository
from domainbot.watchlists.service import build_watch_plan


def create_router() -> Router:
    router = Router(name="domainbot")
    router.message.register(handle_message)
    return router


async def handle_message(
    message: Message,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    text = message.text or ""
    if not text.startswith("/"):
        return

    if not is_group_chat(message.chat):
        return

    if not is_allowed_chat(settings, message.chat.id):
        await message.answer(unauthorized_group())
        return

    try:
        parsed = parse_command(
            text,
            max_domains=settings.max_domains_per_command,
            max_watch_domains=settings.max_domains_per_watch,
        )
    except ParseError as exc:
        await message.answer(invalid_command(exc.usage))
        return

    if parsed.command_type == CommandType.REPORT_RANGE:
        if parsed.root is None or parsed.numeric_range is None:
            await message.answer(command_not_ready())
            return
        report_service = ReportService()
        async with session_factory() as session:
            try:
                report = await report_service.load_range_report(
                    session=session,
                    chat_id=message.chat.id,
                    root=parsed.root,
                    range_start=parsed.numeric_range.start,
                    range_end=parsed.numeric_range.end,
                    report_filter=parsed.report_filter,
                )
            except ReportNotFoundError:
                await message.answer(report_not_found())
                return
        if parsed.wants_excel:
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            filename = safe_report_filename(
                parsed.root,
                parsed.numeric_range.start,
                parsed.numeric_range.end,
                timestamp,
            )
            path = settings.temp_report_dir / filename
            write_excel_report(report, path)
            try:
                await message.answer_document(FSInputFile(path), caption="Excel raporu hazır.")
            finally:
                path.unlink(missing_ok=True)
        else:
            await message.answer(render_text_report(report, settings.report_message_row_limit))
        return

    if parsed.command_type == CommandType.REPORT_GENERAL:
        report_service = ReportService()
        async with session_factory() as session:
            report = await report_service.load_general_report(
                session=session,
                chat_id=message.chat.id,
                report_filter=parsed.report_filter,
            )
        if parsed.wants_excel:
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            path = settings.temp_report_dir / safe_general_report_filename(timestamp)
            write_excel_report(report, path)
            try:
                await message.answer_document(
                    FSInputFile(path),
                    caption="Genel Excel raporu hazır.",
                )
            finally:
                path.unlink(missing_ok=True)
        else:
            await message.answer(render_text_report(report, settings.report_message_row_limit))
        return

    if parsed.command_type in {CommandType.WATCH_SINGLE, CommandType.WATCH_RANGE}:
        user = message.from_user
        if user is None:
            await message.answer(command_not_ready())
            return
        watch_plan = build_watch_plan(parsed)
        repository = WatchlistRepository()
        async with session_factory() as session:
            async with session.begin():
                await repository.create_watchlist(
                    session=session,
                    plan=watch_plan,
                    chat_id=message.chat.id,
                    created_by=user.id,
                )
        await message.answer(watch_added(watch_plan.total_count, watch_plan.frequency))
        return

    if parsed.command_type in {CommandType.UNWATCH_SINGLE, CommandType.UNWATCH_RANGE}:
        watch_plan = build_watch_plan(parsed)
        repository = WatchlistRepository()
        async with session_factory() as session:
            async with session.begin():
                removed = await repository.deactivate_watchlist(
                    session=session,
                    plan=watch_plan,
                    chat_id=message.chat.id,
                )
        await message.answer(watch_removed() if removed else watch_not_found())
        return

    if parsed.command_type == CommandType.LIST_WATCHES:
        repository = WatchlistRepository()
        async with session_factory() as session:
            items = await repository.active_watchlists(session, message.chat.id)
        await message.answer(render_watchlists(items))
        return

    if parsed.command_type == CommandType.POOL_DOMAIN_REFRESH:
        user = message.from_user
        if user is None:
            await message.answer(command_not_ready())
            return
        pool_service = PoolRefreshService()
        async with session_factory() as session:
            async with session.begin():
                result = await pool_service.enqueue_domain_refresh(
                    session=session,
                    chat_id=message.chat.id,
                    requested_by=user.id,
                    batch_size=settings.pool_domain_refresh_batch_size,
                )
        await message.answer(
            pool_domain_refresh_started(
                result.domain_count,
                result.job_count,
                result.already_running,
            )
        )
        return

    if parsed.command_type == CommandType.POOL_BTK_REFRESH:
        pool_service = PoolRefreshService()
        async with session_factory() as session:
            async with session.begin():
                domain_count = await pool_service.enqueue_btk_refresh(session)
        await message.answer(pool_btk_refresh_started(domain_count))
        return

    if parsed.command_type in {CommandType.POOL_DELETE_SINGLE, CommandType.POOL_DELETE_RANGE}:
        pool_service = PoolRefreshService()
        async with session_factory() as session:
            async with session.begin():
                delete_result = await pool_service.delete_domains(
                    session=session,
                    domains=parsed.domains(),
                    chat_id=message.chat.id,
                )
                deactivated_watch_count = delete_result.deactivated_watch_count
                if parsed.root is not None and parsed.numeric_range is not None:
                    deactivated_watch_count += await pool_service.deactivate_exact_range_watchlist(
                        session=session,
                        chat_id=message.chat.id,
                        root=parsed.root,
                        range_start=parsed.numeric_range.start,
                        range_end=parsed.numeric_range.end,
                    )
        await message.answer(
            pool_delete_completed(
                delete_result.requested_count,
                delete_result.deleted_count,
                deactivated_watch_count,
            )
        )
        return

    if parsed.command_type in {CommandType.QUERY_SINGLE, CommandType.QUERY_RANGE}:
        user = message.from_user
        if user is None:
            await message.answer(command_not_ready())
            return
        scan_plan = build_scan_job_plan(parsed)
        scan_service = ScanJobService()
        async with session_factory() as session:
            async with session.begin():
                await scan_service.create_from_command(
                    session=session,
                    parsed=parsed,
                    chat_id=message.chat.id,
                    requested_by=user.id,
                )
        await message.answer(query_accepted(scan_plan))
        return

    await message.answer(command_not_ready())
