from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.web.templating import datetime_user


def test_datetime_display_uses_owner_local_american_standard() -> None:
    timezone = ZoneInfo("America/New_York")
    now = datetime(2026, 8, 3, 18, tzinfo=UTC)

    assert (
        datetime_user(
            datetime(2026, 8, 3, 17, 50, 46, tzinfo=UTC),
            now=now,
            timezone=timezone,
        )
        == "08/03 01:50 pm"
    )
    assert (
        datetime_user(
            datetime(2025, 8, 3, 17, 50, tzinfo=UTC),
            now=now,
            timezone=timezone,
        )
        == "08/03/25 01:50 pm"
    )


def test_datetime_display_can_hide_time() -> None:
    assert (
        datetime_user(
            datetime(2026, 8, 3, 17, 50, tzinfo=UTC),
            show_time=False,
            now=datetime(2026, 8, 3, 18, tzinfo=UTC),
        )
        == "08/03"
    )
