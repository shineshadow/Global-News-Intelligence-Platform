import json
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.templating import Jinja2Templates

WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = WEB_DIR / "templates"
THEME_DIR = WEB_DIR / "themes"


templates = Jinja2Templates(
    directory=[TEMPLATE_DIR, THEME_DIR],
)


DEFAULT_DISPLAY_TIMEZONE = ZoneInfo("America/New_York")


def datetime_user(
    value: datetime | None,
    show_time: bool = True,
    *,
    now: datetime | None = None,
    timezone: ZoneInfo = DEFAULT_DISPLAY_TIMEZONE,
) -> str:
    if value is None:
        return "—"

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    localized = value.astimezone(timezone)
    current = (now or datetime.now(UTC)).astimezone(timezone)
    date_format = "%m/%d" if localized.year == current.year else "%m/%d/%y"
    rendered = localized.strftime(date_format)
    if show_time:
        rendered += " " + localized.strftime("%I:%M %p").lower()
    return rendered


def number(value: int | None) -> str:
    return f"{value or 0:,}"


def json_pretty(
    value,
) -> str:
    if value is None:
        return "{}"

    return json.dumps(
        value,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


templates.env.filters["datetime_user"] = datetime_user
# Compatibility alias while templates migrate to the product-facing name.
templates.env.filters["datetime_utc"] = datetime_user

templates.env.filters["number"] = number

templates.env.filters["json_pretty"] = json_pretty
