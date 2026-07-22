from datetime import UTC, datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates


WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = WEB_DIR / "templates"


templates = Jinja2Templates(
    directory=TEMPLATE_DIR,
)


def datetime_utc(
    value: datetime | None,
) -> str:
    if value is None:
        return "—"

    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)

    return (
        value.astimezone(UTC)
        .strftime("%Y-%m-%d %H:%M:%S UTC")
    )


def number(value: int | None) -> str:
    return f"{value or 0:,}"


templates.env.filters["datetime_utc"] = (
    datetime_utc
)

templates.env.filters["number"] = number