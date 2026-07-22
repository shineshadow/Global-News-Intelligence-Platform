class FeedError(RuntimeError):
    """Base exception for RSS and Atom processing."""


class FeedFetchError(FeedError):
    """Raised when a feed cannot be retrieved."""


class FeedHTTPStatusError(FeedFetchError):
    """Raised when a feed returns an unexpected HTTP status."""

    def __init__(
        self,
        status_code: int,
        url: str,
    ) -> None:
        self.status_code = status_code
        self.url = url

        super().__init__(
            f"Feed request returned HTTP {status_code}: {url}"
        )


class FeedResponseTooLargeError(FeedFetchError):
    """Raised when a feed exceeds the configured size limit."""

    def __init__(
        self,
        max_bytes: int,
        url: str,
    ) -> None:
        self.max_bytes = max_bytes
        self.url = url

        super().__init__(
            f"Feed response exceeded {max_bytes} bytes: {url}"
        )


class FeedParseError(FeedError):
    """Raised when downloaded content is not a usable feed."""