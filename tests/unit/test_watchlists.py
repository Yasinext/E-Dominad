from __future__ import annotations

from datetime import UTC, datetime, timedelta

from domainbot.db.models import Watchlist
from domainbot.watchlists.repository import _batch_plan, _next_cursor, _next_run_at


def test_batch_plan_spreads_range_from_cursor() -> None:
    watchlist = Watchlist(
        chat_id=1,
        created_by=1,
        watch_type="range",
        root="test",
        range_start=1,
        range_end=2000,
        range_width=1,
        scan_cursor=301,
        frequency="gunluk",
        next_run_at=datetime(2026, 8, 1, tzinfo=UTC),
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    plan = _batch_plan(watchlist, batch_size=300)

    assert plan.range_start == 301
    assert plan.range_end == 600
    assert plan.total_count == 300
    assert plan.domains[0] == "test301.com"
    assert plan.domains[-1] == "test600.com"


def test_next_cursor_wraps_to_start() -> None:
    watchlist = Watchlist(
        chat_id=1,
        created_by=1,
        watch_type="range",
        root="test",
        range_start=1,
        range_end=500,
        range_width=1,
        scan_cursor=301,
        frequency="gunluk",
        next_run_at=datetime(2026, 8, 1, tzinfo=UTC),
        created_at=datetime(2026, 8, 1, tzinfo=UTC),
        updated_at=datetime(2026, 8, 1, tzinfo=UTC),
    )

    assert _next_cursor(watchlist, batch_size=300) == 1


def test_next_run_at_uses_daily_frequency() -> None:
    run_at = datetime(2026, 8, 1, 9, 30, tzinfo=UTC)

    assert _next_run_at(run_at, "gunluk") == run_at + timedelta(days=1)


def test_next_run_at_uses_weekly_frequency() -> None:
    run_at = datetime(2026, 8, 1, 9, 30, tzinfo=UTC)

    assert _next_run_at(run_at, "haftalik") == run_at + timedelta(days=7)
