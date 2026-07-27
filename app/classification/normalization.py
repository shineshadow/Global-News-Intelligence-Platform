import html
import re
import unicodedata


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_match_text(value: str | None) -> str:
    """Normalize text for deterministic matching across scripts."""
    if not value:
        return ""

    without_tags = _HTML_TAG_RE.sub(" ", html.unescape(value))
    normalized = unicodedata.normalize("NFKC", without_tags).casefold()
    return _WHITESPACE_RE.sub(" ", normalized).strip()


def normalize_alias(value: str) -> str:
    """Normalize an entity alias using the same matching semantics."""
    return normalize_match_text(value)
