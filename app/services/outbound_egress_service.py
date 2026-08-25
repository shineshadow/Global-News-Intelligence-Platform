from __future__ import annotations

import asyncio
import ipaddress
import socket
import ssl
from collections.abc import AsyncIterator, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Protocol

import httpx

REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
STANDARD_CREDENTIAL_HEADERS = frozenset(
    {"authorization", "proxy-authorization", "cookie"}
)
CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
CLOUD_METADATA_ADDRESSES = frozenset(
    {
        ipaddress.ip_address("169.254.169.254"),
        ipaddress.ip_address("100.100.100.200"),
        ipaddress.ip_address("192.0.0.192"),
        ipaddress.ip_address("fd00:ec2::254"),
    }
)


class OutboundEgressError(RuntimeError):
    """Base failure for guarded outbound retrieval."""

    def __init__(self, message: str, *, reason_code: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message)


class OutboundDestinationRejected(OutboundEgressError):
    """A URL, resolved address, redirect, or internal identity was refused."""


class OutboundTransportError(OutboundEgressError):
    """The pinned transport failed or could not prove its connected peer."""


class OutboundResponseLimitError(OutboundEgressError):
    """A response exceeded an installation-owned hard limit."""


class ControlledResolver(Protocol):
    async def resolve(self, hostname: str, port: int) -> tuple[str, ...]: ...


class PinnedHTTPTransport(Protocol):
    def stream(
        self,
        *,
        method: str,
        url: httpx.URL,
        headers: Mapping[str, str],
        sni_hostname: str | None,
        timeout: httpx.Timeout,
    ) -> AbstractAsyncContextManager[httpx.Response]: ...


@dataclass(frozen=True)
class InternalServiceRegistration:
    identity: str
    adapter_slug: str
    scheme: str
    hostname: str
    port: int
    address_networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
    tls_policy: str
    purpose: str

    def __post_init__(self) -> None:
        required = (
            self.identity,
            self.adapter_slug,
            self.hostname,
            self.purpose,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Internal-service identity fields must be non-empty.")
        if self.scheme not in {"http", "https"}:
            raise ValueError("Internal-service scheme must be HTTP or HTTPS.")
        if not 1 <= self.port <= 65535:
            raise ValueError("Internal-service port is invalid.")
        if self.tls_policy not in {"public_ca", "plaintext_internal"}:
            raise ValueError("Internal-service TLS policy is unsupported.")
        if self.scheme == "https" and self.tls_policy != "public_ca":
            raise ValueError("HTTPS internal services require public CA verification.")
        if self.scheme == "http" and self.tls_policy != "plaintext_internal":
            raise ValueError("Plaintext internal services require explicit policy.")
        if not self.address_networks:
            raise ValueError("Internal service requires at least one exact address network.")
        if any(
            not isinstance(
                network,
                (ipaddress.IPv4Network, ipaddress.IPv6Network),
            )
            for network in self.address_networks
        ):
            raise ValueError("Internal-service address networks must be parsed networks.")
        normalized_hostname = _normalize_hostname(self.hostname)
        object.__setattr__(self, "hostname", normalized_hostname)


class InternalServiceRegistry:
    """Trusted installation registrations; never populated by Source data."""

    def __init__(
        self,
        registrations: tuple[InternalServiceRegistration, ...] = (),
    ) -> None:
        by_identity: dict[str, InternalServiceRegistration] = {}
        for registration in registrations:
            if registration.identity in by_identity:
                raise ValueError(
                    f"Duplicate internal-service identity {registration.identity!r}."
                )
            by_identity[registration.identity] = registration
        self._by_identity = by_identity

    def require(self, identity: str) -> InternalServiceRegistration:
        try:
            return self._by_identity[identity]
        except KeyError as exc:
            raise OutboundDestinationRejected(
                "Internal-service identity is not installation-registered."
            ) from exc


@dataclass(frozen=True)
class EgressRequestPolicy:
    adapter_slug: str
    allowed_schemes: frozenset[str]
    internal_service_identity: str | None = None
    credential_header_names: frozenset[str] = field(
        default_factory=lambda: STANDARD_CREDENTIAL_HEADERS
    )
    credential_query_keys: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.adapter_slug.strip():
            raise ValueError("Adapter slug is required.")
        if not self.allowed_schemes or not self.allowed_schemes <= {"http", "https"}:
            raise ValueError("Adapter schemes must be a non-empty HTTP/HTTPS subset.")
        normalized_headers = frozenset(
            value.strip().lower() for value in self.credential_header_names
        )
        normalized_query = frozenset(
            value.strip() for value in self.credential_query_keys
        )
        if any(not value for value in normalized_headers | normalized_query):
            raise ValueError("Credential names must be non-empty.")
        object.__setattr__(self, "credential_header_names", normalized_headers)
        object.__setattr__(self, "credential_query_keys", normalized_query)


@dataclass(frozen=True)
class OutboundResponseLimits:
    max_redirects: int = 5
    max_header_bytes: int = 64 * 1024
    max_response_bytes: int = 10 * 1024 * 1024
    total_seconds: float = 60.0
    connect_seconds: float = 10.0
    read_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_redirects < 0:
            raise ValueError("Redirect limit cannot be negative.")
        values = (
            self.max_header_bytes,
            self.max_response_bytes,
            self.total_seconds,
            self.connect_seconds,
            self.read_seconds,
        )
        if any(value <= 0 for value in values):
            raise ValueError("Outbound response limits must be positive.")


@dataclass(frozen=True)
class ValidatedDestination:
    url: httpx.URL
    hostname: str
    port: int
    addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]
    selected_address: ipaddress.IPv4Address | ipaddress.IPv6Address
    internal_service_identity: str | None

    @property
    def origin(self) -> tuple[str, str, int]:
        return (self.url.scheme, self.hostname, self.port)


@dataclass(frozen=True)
class GuardedHTTPResponse:
    requested_url: str
    final_url: str
    status_code: int
    headers: httpx.Headers
    content: bytes
    response_bytes: int
    connected_address: str
    redirect_count: int


class AsyncioControlledResolver:
    async def resolve(self, hostname: str, port: int) -> tuple[str, ...]:
        loop = asyncio.get_running_loop()
        try:
            rows = await loop.getaddrinfo(
                hostname,
                port,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
        except OSError as exc:
            raise OutboundDestinationRejected(
                "Controlled DNS resolution failed.",
                reason_code="dns_failure",
            ) from exc
        addresses: list[str] = []
        for _, _, _, _, socket_address in rows:
            address = str(socket_address[0])
            if address not in addresses:
                addresses.append(address)
        if not addresses:
            raise OutboundDestinationRejected(
                "Controlled DNS resolution returned no addresses.",
                reason_code="dns_failure",
            )
        return tuple(addresses)


class OutboundEgressGuard:
    def __init__(
        self,
        *,
        resolver: ControlledResolver | None = None,
        internal_services: InternalServiceRegistry | None = None,
    ) -> None:
        self._resolver = resolver or AsyncioControlledResolver()
        self._internal_services = internal_services or InternalServiceRegistry()

    async def validate(
        self,
        raw_url: str | httpx.URL,
        policy: EgressRequestPolicy,
    ) -> ValidatedDestination:
        try:
            url = raw_url if isinstance(raw_url, httpx.URL) else httpx.URL(raw_url)
        except (TypeError, httpx.InvalidURL) as exc:
            raise OutboundDestinationRejected("Outbound URL is invalid.") from exc
        if len(str(url)) > 8192:
            raise OutboundDestinationRejected("Outbound URL exceeds its length limit.")
        if url.scheme not in policy.allowed_schemes:
            raise OutboundDestinationRejected(
                "URL scheme is not approved for the exact adapter."
            )
        if url.username or url.password:
            raise OutboundDestinationRejected(
                "User-info credentials are forbidden in outbound URLs."
            )
        if not url.host:
            raise OutboundDestinationRejected("Outbound URL requires a hostname.")
        try:
            hostname = _normalize_hostname(url.host)
        except ValueError as exc:
            raise OutboundDestinationRejected(
                "Outbound hostname normalization failed."
            ) from exc
        if _is_forbidden_hostname(hostname):
            raise OutboundDestinationRejected("Local-use hostname is forbidden.")
        port = url.port or (443 if url.scheme == "https" else 80)
        if not 1 <= port <= 65535:
            raise OutboundDestinationRejected("Outbound URL port is invalid.")

        addresses = await self._resolve_addresses(hostname, port)
        internal_identity = policy.internal_service_identity
        if internal_identity is None:
            for address in addresses:
                _require_public_address(address)
        else:
            registration = self._internal_services.require(internal_identity)
            self._validate_internal_registration(
                registration=registration,
                policy=policy,
                scheme=url.scheme,
                hostname=hostname,
                port=port,
                addresses=addresses,
            )
        return ValidatedDestination(
            url=url.copy_with(fragment=None),
            hostname=hostname,
            port=port,
            addresses=addresses,
            selected_address=addresses[0],
            internal_service_identity=internal_identity,
        )

    async def _resolve_addresses(
        self,
        hostname: str,
        port: int,
    ) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
        try:
            literal = ipaddress.ip_address(hostname)
        except ValueError:
            raw_addresses = await self._resolver.resolve(hostname, port)
        else:
            raw_addresses = (str(literal),)
        addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
        for raw_address in raw_addresses:
            try:
                address = ipaddress.ip_address(raw_address)
            except ValueError as exc:
                raise OutboundDestinationRejected(
                    "Controlled resolver returned an invalid address."
                ) from exc
            if address not in addresses:
                addresses.append(address)
        if not addresses:
            raise OutboundDestinationRejected(
                "Controlled resolver returned no usable addresses."
            )
        return tuple(addresses)

    @staticmethod
    def _validate_internal_registration(
        *,
        registration: InternalServiceRegistration,
        policy: EgressRequestPolicy,
        scheme: str,
        hostname: str,
        port: int,
        addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...],
    ) -> None:
        if (
            registration.adapter_slug != policy.adapter_slug
            or registration.scheme != scheme
            or registration.hostname != hostname
            or registration.port != port
        ):
            raise OutboundDestinationRejected(
                "Outbound target does not match its internal-service registration."
            )
        if any(
            not any(address in network for network in registration.address_networks)
            for address in addresses
        ):
            raise OutboundDestinationRejected(
                "Resolved address escaped the internal-service registration."
            )


class HttpxPinnedTransport:
    """One fresh pool per hop so SNI can never cross validated origins."""

    def __init__(self) -> None:
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        self._ssl_context = context

    @asynccontextmanager
    async def stream(
        self,
        *,
        method: str,
        url: httpx.URL,
        headers: Mapping[str, str],
        sni_hostname: str | None,
        timeout: httpx.Timeout,
    ) -> AsyncIterator[httpx.Response]:
        extensions = {"sni_hostname": sni_hostname} if sni_hostname else {}
        try:
            async with httpx.AsyncClient(
                verify=self._ssl_context,
                follow_redirects=False,
                trust_env=False,
                timeout=timeout,
            ) as client, client.stream(
                method,
                url,
                headers=headers,
                extensions=extensions,
                follow_redirects=False,
            ) as response:
                yield response
        except httpx.RequestError as exc:
            raise OutboundTransportError(
                "Pinned outbound transport failed."
            ) from exc


class GuardedHTTPClient:
    def __init__(
        self,
        *,
        guard: OutboundEgressGuard | None = None,
        transport: PinnedHTTPTransport | None = None,
        limits: OutboundResponseLimits | None = None,
    ) -> None:
        self._guard = guard or OutboundEgressGuard()
        self._transport = transport or HttpxPinnedTransport()
        self._limits = limits or OutboundResponseLimits()

    async def get(
        self,
        url: str,
        *,
        policy: EgressRequestPolicy,
        headers: Mapping[str, str] | None = None,
    ) -> GuardedHTTPResponse:
        request_headers = _normalize_request_headers(headers or {})
        requested_url = url
        current_url = httpx.URL(url)
        previous_origin: tuple[str, str, int] | None = None
        redirect_count = 0
        timeout = httpx.Timeout(
            connect=self._limits.connect_seconds,
            read=self._limits.read_seconds,
            write=self._limits.connect_seconds,
            pool=self._limits.connect_seconds,
        )
        try:
            async with asyncio.timeout(self._limits.total_seconds):
                while True:
                    try:
                        destination = await self._guard.validate(current_url, policy)
                    except OutboundDestinationRejected as exc:
                        if redirect_count:
                            raise OutboundDestinationRejected(
                                "Outbound redirect destination was rejected.",
                                reason_code="redirect_destination_rejected",
                            ) from exc
                        raise
                    if (
                        previous_origin is not None
                        and destination.origin != previous_origin
                    ):
                        request_headers = {
                            key: value
                            for key, value in request_headers.items()
                            if key.lower() not in policy.credential_header_names
                        }
                        if _contains_query_credentials(
                            destination.url,
                            policy.credential_query_keys,
                        ):
                            raise OutboundDestinationRejected(
                                "Cross-origin redirect attempted to forward query credentials."
                            )
                    connect_url = destination.url.copy_with(
                        host=destination.selected_address.compressed
                    )
                    hop_headers = dict(request_headers)
                    hop_headers["Host"] = _host_header(destination)
                    sni_hostname = (
                        destination.hostname
                        if destination.url.scheme == "https"
                        else None
                    )
                    async with self._transport.stream(
                        method="GET",
                        url=connect_url,
                        headers=hop_headers,
                        sni_hostname=sni_hostname,
                        timeout=timeout,
                    ) as response:
                        peer_address = _verified_peer_address(
                            response,
                            destination.selected_address,
                        )
                        _enforce_header_limit(
                            response.headers,
                            self._limits.max_header_bytes,
                        )
                        if (
                            response.status_code in REDIRECT_STATUS_CODES
                            and response.headers.get("Location") is not None
                        ):
                            if redirect_count >= self._limits.max_redirects:
                                raise OutboundResponseLimitError(
                                    "Outbound redirect limit was exceeded.",
                                    reason_code="redirect_limit_reached",
                                )
                            redirect_url = destination.url.join(
                                response.headers["Location"]
                            )
                            if (
                                destination.url.scheme == "https"
                                and redirect_url.scheme == "http"
                            ):
                                raise OutboundDestinationRejected(
                                    "HTTPS downgrade redirect is forbidden."
                                )
                            previous_origin = destination.origin
                            current_url = redirect_url
                            redirect_count += 1
                            continue
                        content = await _read_limited_body(
                            response,
                            self._limits.max_response_bytes,
                        )
                        return GuardedHTTPResponse(
                            requested_url=_redacted_url(
                                httpx.URL(requested_url),
                                policy.credential_query_keys,
                            ),
                            final_url=_redacted_url(
                                destination.url,
                                policy.credential_query_keys,
                            ),
                            status_code=response.status_code,
                            headers=_sanitized_response_headers(
                                response.headers,
                                destination.url,
                                policy.credential_query_keys,
                            ),
                            content=content,
                            response_bytes=len(content),
                            connected_address=peer_address.compressed,
                            redirect_count=redirect_count,
                        )
        except TimeoutError as exc:
            raise OutboundResponseLimitError(
                "Outbound request exceeded its total duration limit.",
                reason_code="read_timeout",
            ) from exc


def _normalize_hostname(hostname: str) -> str:
    candidate = hostname.rstrip(".").lower()
    if not candidate or "%" in candidate:
        raise ValueError("Hostname is empty or contains an IPv6 zone identifier.")
    try:
        return candidate.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Hostname IDNA normalization failed.") from exc


def _is_forbidden_hostname(hostname: str) -> bool:
    return (
        hostname in {"localhost", "home.arpa"}
        or hostname.endswith((".localhost", ".local", ".home.arpa"))
    )


def _require_public_address(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> None:
    effective = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) else None
    checked = effective or address
    if (
        checked in CLOUD_METADATA_ADDRESSES
        or (
            isinstance(checked, ipaddress.IPv4Address)
            and checked in CGNAT_NETWORK
        )
        or checked.is_loopback
        or checked.is_link_local
        or checked.is_multicast
        or checked.is_unspecified
        or checked.is_private
        or checked.is_reserved
    ):
        raise OutboundDestinationRejected(
            "Resolved address is forbidden by public egress policy."
        )


def _normalize_request_headers(headers: Mapping[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for name, value in headers.items():
        if not name.strip() or "\r" in name or "\n" in name:
            raise ValueError("Outbound header name is invalid.")
        if "\r" in value or "\n" in value:
            raise ValueError("Outbound header value is invalid.")
        if name.lower() == "host":
            raise ValueError("Outbound Host header is controlled by the egress guard.")
        normalized[name] = value
    return normalized


def _host_header(destination: ValidatedDestination) -> str:
    default_port = 443 if destination.url.scheme == "https" else 80
    hostname = destination.hostname
    if ":" in hostname:
        hostname = f"[{hostname}]"
    return hostname if destination.port == default_port else f"{hostname}:{destination.port}"


def _contains_query_credentials(
    url: httpx.URL,
    credential_query_keys: frozenset[str],
) -> bool:
    if not credential_query_keys:
        return False
    return any(key in credential_query_keys for key, _ in url.params.multi_items())


def _verified_peer_address(
    response: httpx.Response,
    expected: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    raw_peer = response.extensions.get("gni_peer_ip")
    if raw_peer is None:
        network_stream = response.extensions.get("network_stream")
        if network_stream is not None:
            server_address = network_stream.get_extra_info("server_addr")
            if isinstance(server_address, tuple) and server_address:
                raw_peer = server_address[0]
    try:
        peer = ipaddress.ip_address(str(raw_peer))
    except ValueError as exc:
        raise OutboundTransportError(
            "Pinned transport did not expose a valid connected peer."
        ) from exc
    if peer != expected:
        raise OutboundTransportError(
            "Connected peer disagrees with the validated pinned address."
        )
    return peer


def _enforce_header_limit(headers: httpx.Headers, byte_limit: int) -> None:
    total = sum(len(name) + len(value) + 4 for name, value in headers.raw)
    if total > byte_limit:
        raise OutboundResponseLimitError(
            "Outbound response headers exceeded their byte limit.",
            reason_code="response_too_large",
        )


async def _read_limited_body(
    response: httpx.Response,
    byte_limit: int,
) -> bytes:
    raw_length = response.headers.get("Content-Length")
    if raw_length is not None:
        try:
            declared_length = int(raw_length)
        except ValueError as exc:
            raise OutboundTransportError(
                "Outbound response declared an invalid Content-Length."
            ) from exc
        if declared_length < 0:
            raise OutboundTransportError(
                "Outbound response declared a negative Content-Length."
            )
        if declared_length > byte_limit:
            raise OutboundResponseLimitError(
                "Outbound response exceeded its declared byte limit.",
                reason_code="response_too_large",
            )
    content = bytearray()
    async for chunk in response.aiter_bytes():
        content.extend(chunk)
        if len(content) > byte_limit:
            raise OutboundResponseLimitError(
                "Outbound response exceeded its streaming byte limit.",
                reason_code="response_too_large",
            )
    return bytes(content)


def _redacted_url(
    url: httpx.URL,
    credential_query_keys: frozenset[str],
) -> str:
    if not credential_query_keys:
        return str(url)
    pairs = [
        (key, "[REDACTED]" if key in credential_query_keys else value)
        for key, value in url.params.multi_items()
    ]
    query = str(httpx.QueryParams(pairs))
    return str(url.copy_with(query=query.encode("ascii")))


def _sanitized_response_headers(
    headers: httpx.Headers,
    response_url: httpx.URL,
    credential_query_keys: frozenset[str],
) -> httpx.Headers:
    sanitized: list[tuple[str, str]] = []
    for name, value in headers.multi_items():
        lowered = name.lower()
        if lowered in {"set-cookie", "authorization", "proxy-authorization"}:
            continue
        if lowered == "location":
            try:
                value = _redacted_url(
                    response_url.join(value),
                    credential_query_keys,
                )
            except httpx.InvalidURL:
                value = "[INVALID LOCATION]"
        sanitized.append((name, value))
    return httpx.Headers(sanitized)
