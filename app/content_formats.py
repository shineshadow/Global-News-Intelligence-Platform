"""Normalize observed media types to canonical GFA-D content formats."""


_EXACT_MEDIA_TYPES = {
    "application/epub+zip": "ebook",
    "application/gzip": "archive",
    "application/json": "json",
    "application/msword": "word_processing",
    "application/octet-stream": "binary",
    "application/pdf": "pdf",
    "application/vnd.ms-excel": "spreadsheet",
    "application/vnd.ms-powerpoint": "presentation",
    "application/vnd.oasis.opendocument.presentation": "presentation",
    "application/vnd.oasis.opendocument.spreadsheet": "spreadsheet",
    "application/vnd.oasis.opendocument.text": "word_processing",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (
        "presentation"
    ),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (
        "spreadsheet"
    ),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (
        "word_processing"
    ),
    "application/vnd.rar": "archive",
    "application/x-7z-compressed": "archive",
    "application/x-tar": "archive",
    "application/xhtml+xml": "html",
    "application/xml": "xml",
    "application/zip": "archive",
    "message/rfc822": "email_message",
    "text/calendar": "calendar",
    "text/csv": "csv",
    "text/html": "html",
    "text/markdown": "markdown",
    "text/plain": "plain_text",
    "text/tab-separated-values": "tsv",
    "text/xml": "xml",
}


def normalize_content_format(media_type: str | None) -> str:
    """Return a canonical content-format slug for an observed media type."""

    if media_type is None:
        return "unknown"

    normalized = media_type.partition(";")[0].strip().lower()
    if not normalized:
        return "unknown"

    exact = _EXACT_MEDIA_TYPES.get(normalized)
    if exact is not None:
        return exact

    if normalized.endswith("+json"):
        return "json"
    if normalized.endswith("+xml"):
        return "xml"
    if normalized.startswith("image/"):
        return "image"
    if normalized.startswith("audio/"):
        return "audio"
    if normalized.startswith("video/"):
        return "video"

    return "other"
