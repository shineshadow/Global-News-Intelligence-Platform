from __future__ import annotations

import asyncio
import gzip
import ipaddress
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import httpx
import pytest

from app.services.outbound_egress_service import (
    EgressRequestPolicy,
    GuardedHTTPClient,
    InternalServiceRegistration,
    InternalServiceRegistry,
    OutboundDestinationRejected,
    OutboundEgressGuard,
    OutboundResponseLimitError,
    OutboundResponseLimits,
    OutboundTransportError,
)

PUBLIC_POLICY = EgressRequestPolicy(
    adapter_slug="test-http",
    allowed_schemes=frozenset({"http", "https"}),
)


class StaticResolver:
    def __init__(self, answers: Mapping[str, tuple[str, ...]]) -> None:
        self.answers = dict(answers)
        self.calls: list[tuple[str, int]] = []

    async def resolve(self, hostname: str, port: int) -> tuple[str, ...]:
        self.calls.append((hostname, port))
        return self.answers[hostname]


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks: tuple[bytes, ...]) -> None:
        self._chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


@dataclass(frozen=True)
class ResponseSpec:
    status_code: int = 200
    headers: Mapping[str, str] = field(default_factory=dict)
    chunks: tuple[bytes, ...] = (b"ok",)
    peer_ip: str = "93.184.216.34"
    delay_seconds: float = 0


@dataclass(frozen=True)
class TransportRecord:
    method: str
    url: httpx.URL
    headers: dict[str, str]
    sni_hostname: str | None


class FakePinnedTransport:
    def __init__(self, *responses: ResponseSpec) -> None:
        self.responses = list(responses)
        self.records: list[TransportRecord] = []

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
        del timeout
        self.records.append(
            TransportRecord(
                method=method,
                url=url,
                headers=dict(headers),
                sni_hostname=sni_hostname,
            )
        )
        specification = self.responses.pop(0)
        if specification.delay_seconds:
            await asyncio.sleep(specification.delay_seconds)
        yield httpx.Response(
            specification.status_code,
            headers=specification.headers,
            stream=ChunkStream(specification.chunks),
            request=httpx.Request(method, url),
            extensions={"gni_peer_ip": specification.peer_ip},
        )


def _client(
    resolver: StaticResolver,
    transport: FakePinnedTransport,
    *,
    limits: OutboundResponseLimits | None = None,
    registry: InternalServiceRegistry | None = None,
) -> GuardedHTTPClient:
    return GuardedHTTPClient(
        guard=OutboundEgressGuard(
            resolver=resolver,
            internal_services=registry,
        ),
        transport=transport,
        limits=limits,
    )


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "100.100.100.200",
        "192.0.0.192",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fc00::1",
        "fe80::1",
        "ff02::1",
        "::ffff:127.0.0.1",
    ],
)
async def test_public_guard_rejects_forbidden_addresses(address) -> None:
    guard = OutboundEgressGuard(
        resolver=StaticResolver({"blocked.test": (address,)})
    )

    with pytest.raises(OutboundDestinationRejected):
        await guard.validate("https://blocked.test/feed", PUBLIC_POLICY)


async def test_mixed_public_and_private_dns_answer_fails_closed() -> None:
    guard = OutboundEgressGuard(
        resolver=StaticResolver(
            {"mixed.test": ("93.184.216.34", "127.0.0.1")}
        )
    )

    with pytest.raises(OutboundDestinationRejected):
        await guard.validate("https://mixed.test/feed", PUBLIC_POLICY)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:secret@example.test/feed",
        "http://localhost/feed",
        "http://service.local/feed",
        "http://service.home.arpa/feed",
    ],
)
async def test_url_shape_and_local_names_are_rejected(url) -> None:
    guard = OutboundEgressGuard(
        resolver=StaticResolver({"example.test": ("93.184.216.34",)})
    )

    with pytest.raises(OutboundDestinationRejected):
        await guard.validate(url, PUBLIC_POLICY)


async def test_request_connects_to_validated_ip_with_original_host_and_sni() -> None:
    resolver = StaticResolver({"example.test": ("93.184.216.34",)})
    transport = FakePinnedTransport(
        ResponseSpec(headers={"Content-Type": "text/plain"}, chunks=(b"a", b"b"))
    )
    client = _client(resolver, transport)

    response = await client.get(
        "https://example.test:8443/feed?q=one",
        policy=PUBLIC_POLICY,
        headers={"Accept": "application/rss+xml"},
    )

    assert response.content == b"ab"
    assert response.final_url == "https://example.test:8443/feed?q=one"
    assert response.connected_address == "93.184.216.34"
    record = transport.records[0]
    assert record.url.host == "93.184.216.34"
    assert record.url.port == 8443
    assert record.headers["Host"] == "example.test:8443"
    assert record.sni_hostname == "example.test"


async def test_connected_peer_must_equal_the_validated_address() -> None:
    resolver = StaticResolver({"example.test": ("93.184.216.34",)})
    transport = FakePinnedTransport(
        ResponseSpec(peer_ip="93.184.216.35")
    )

    with pytest.raises(OutboundTransportError, match="disagrees"):
        await _client(resolver, transport).get(
            "https://example.test/feed",
            policy=PUBLIC_POLICY,
        )


async def test_every_redirect_is_resolved_and_private_target_is_blocked() -> None:
    resolver = StaticResolver(
        {
            "public.test": ("93.184.216.34",),
            "private.test": ("127.0.0.1",),
        }
    )
    transport = FakePinnedTransport(
        ResponseSpec(
            status_code=302,
            headers={"Location": "http://private.test/admin"},
            chunks=(),
        )
    )

    with pytest.raises(OutboundDestinationRejected):
        await _client(resolver, transport).get(
            "http://public.test/feed",
            policy=PUBLIC_POLICY,
        )

    assert resolver.calls == [("public.test", 80), ("private.test", 80)]
    assert len(transport.records) == 1


async def test_cross_origin_redirect_strips_all_declared_credentials() -> None:
    resolver = StaticResolver(
        {
            "one.test": ("93.184.216.34",),
            "two.test": ("93.184.216.35",),
        }
    )
    transport = FakePinnedTransport(
        ResponseSpec(
            status_code=302,
            headers={"Location": "https://two.test/next"},
            chunks=(),
        ),
        ResponseSpec(peer_ip="93.184.216.35", chunks=(b"done",)),
    )
    policy = EgressRequestPolicy(
        adapter_slug="test-http",
        allowed_schemes=frozenset({"https"}),
        credential_header_names=frozenset(
            {"authorization", "cookie", "x-api-key"}
        ),
        credential_query_keys=frozenset({"api_key"}),
    )

    response = await _client(resolver, transport).get(
        "https://one.test/feed?api_key=secret",
        policy=policy,
        headers={
            "Authorization": "Bearer secret",
            "Cookie": "session=secret",
            "X-Api-Key": "secret",
            "Accept": "application/json",
        },
    )

    assert response.content == b"done"
    assert response.requested_url == (
        "https://one.test/feed?api_key=%5BREDACTED%5D"
    )
    second_headers = {
        key.lower(): value for key, value in transport.records[1].headers.items()
    }
    assert "authorization" not in second_headers
    assert "cookie" not in second_headers
    assert "x-api-key" not in second_headers
    assert second_headers["accept"] == "application/json"
    assert "api_key" not in transport.records[1].url.params


async def test_cross_origin_redirect_cannot_introduce_query_credentials() -> None:
    resolver = StaticResolver(
        {
            "one.test": ("93.184.216.34",),
            "two.test": ("93.184.216.35",),
        }
    )
    transport = FakePinnedTransport(
        ResponseSpec(
            status_code=302,
            headers={"Location": "https://two.test/next?api_key=secret"},
            chunks=(),
        )
    )
    policy = EgressRequestPolicy(
        adapter_slug="test-http",
        allowed_schemes=frozenset({"https"}),
        credential_query_keys=frozenset({"api_key"}),
    )

    with pytest.raises(OutboundDestinationRejected, match="query credentials"):
        await _client(resolver, transport).get(
            "https://one.test/feed",
            policy=policy,
        )


async def test_https_redirect_cannot_downgrade_to_http() -> None:
    resolver = StaticResolver({"one.test": ("93.184.216.34",)})
    transport = FakePinnedTransport(
        ResponseSpec(
            status_code=302,
            headers={"Location": "http://one.test/next"},
            chunks=(),
        )
    )

    with pytest.raises(OutboundDestinationRejected, match="downgrade"):
        await _client(resolver, transport).get(
            "https://one.test/feed",
            policy=PUBLIC_POLICY,
        )


async def test_redirect_count_is_bounded() -> None:
    resolver = StaticResolver({"loop.test": ("93.184.216.34",)})
    redirect = ResponseSpec(
        status_code=302,
        headers={"Location": "/again"},
        chunks=(),
    )
    transport = FakePinnedTransport(redirect, redirect)

    with pytest.raises(OutboundResponseLimitError, match="redirect"):
        await _client(
            resolver,
            transport,
            limits=OutboundResponseLimits(max_redirects=1),
        ).get("https://loop.test/start", policy=PUBLIC_POLICY)


@pytest.mark.parametrize(
    "specification",
    [
        ResponseSpec(headers={"X-Large": "x" * 100}),
        ResponseSpec(headers={"Content-Length": "1000"}, chunks=(b"small",)),
        ResponseSpec(chunks=(b"12345", b"67890")),
    ],
)
async def test_headers_declared_bytes_and_streaming_bytes_are_bounded(
    specification,
) -> None:
    resolver = StaticResolver({"limit.test": ("93.184.216.34",)})
    transport = FakePinnedTransport(specification)
    limits = OutboundResponseLimits(
        max_header_bytes=64,
        max_response_bytes=8,
    )

    with pytest.raises(OutboundResponseLimitError):
        await _client(resolver, transport, limits=limits).get(
            "https://limit.test/feed",
            policy=PUBLIC_POLICY,
        )


async def test_invalid_content_length_is_rejected() -> None:
    resolver = StaticResolver({"limit.test": ("93.184.216.34",)})
    transport = FakePinnedTransport(
        ResponseSpec(headers={"Content-Length": "not-a-number"})
    )

    with pytest.raises(OutboundTransportError, match="Content-Length"):
        await _client(resolver, transport).get(
            "https://limit.test/feed",
            policy=PUBLIC_POLICY,
        )


async def test_decoded_body_size_is_bounded_after_content_encoding() -> None:
    resolver = StaticResolver({"limit.test": ("93.184.216.34",)})
    compressed = gzip.compress(b"x" * 1000)
    transport = FakePinnedTransport(
        ResponseSpec(
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(compressed)),
            },
            chunks=(compressed,),
        )
    )

    with pytest.raises(OutboundResponseLimitError, match="streaming"):
        await _client(
            resolver,
            transport,
            limits=OutboundResponseLimits(max_response_bytes=100),
        ).get(
            "https://limit.test/feed",
            policy=PUBLIC_POLICY,
        )


async def test_returned_metadata_redacts_credentials_and_cookie_headers() -> None:
    resolver = StaticResolver({"safe.test": ("93.184.216.34",)})
    transport = FakePinnedTransport(
        ResponseSpec(
            headers={
                "Set-Cookie": "session=secret",
                "Location": "/result?api_key=secret&item=1",
                "Content-Type": "text/plain",
            }
        )
    )
    policy = EgressRequestPolicy(
        adapter_slug="test-http",
        allowed_schemes=frozenset({"https"}),
        credential_query_keys=frozenset({"api_key"}),
    )

    response = await _client(resolver, transport).get(
        "https://safe.test/feed?api_key=secret",
        policy=policy,
    )

    assert response.requested_url == (
        "https://safe.test/feed?api_key=%5BREDACTED%5D"
    )
    assert response.final_url == (
        "https://safe.test/feed?api_key=%5BREDACTED%5D"
    )
    assert "set-cookie" not in response.headers
    assert response.headers["Location"] == (
        "https://safe.test/result?api_key=%5BREDACTED%5D&item=1"
    )


async def test_total_duration_is_bounded() -> None:
    resolver = StaticResolver({"slow.test": ("93.184.216.34",)})
    transport = FakePinnedTransport(
        ResponseSpec(delay_seconds=0.2)
    )
    limits = OutboundResponseLimits(total_seconds=0.05)

    with pytest.raises(OutboundResponseLimitError, match="duration"):
        await _client(resolver, transport, limits=limits).get(
            "https://slow.test/feed",
            policy=PUBLIC_POLICY,
        )


async def test_exact_internal_registration_allows_only_its_adapter_target() -> None:
    registration = InternalServiceRegistration(
        identity="local-rsshub",
        adapter_slug="rsshub",
        scheme="http",
        hostname="rsshub.gni.internal",
        port=1200,
        address_networks=(ipaddress.ip_network("10.55.0.0/24"),),
        tls_policy="plaintext_internal",
        purpose="local RSSHub acquisition",
    )
    registry = InternalServiceRegistry((registration,))
    resolver = StaticResolver(
        {"rsshub.gni.internal": ("10.55.0.10",)}
    )
    guard = OutboundEgressGuard(
        resolver=resolver,
        internal_services=registry,
    )
    policy = EgressRequestPolicy(
        adapter_slug="rsshub",
        allowed_schemes=frozenset({"http"}),
        internal_service_identity="local-rsshub",
    )

    destination = await guard.validate(
        "http://rsshub.gni.internal:1200/feed",
        policy,
    )

    assert destination.selected_address == ipaddress.ip_address("10.55.0.10")
    assert destination.internal_service_identity == "local-rsshub"

    with pytest.raises(OutboundDestinationRejected):
        await guard.validate(
            "http://rsshub.gni.internal:1200/feed",
            EgressRequestPolicy(
                adapter_slug="direct-http",
                allowed_schemes=frozenset({"http"}),
                internal_service_identity="local-rsshub",
            ),
        )

    with pytest.raises(OutboundDestinationRejected):
        await OutboundEgressGuard(resolver=resolver).validate(
            "http://rsshub.gni.internal:1200/feed",
            EgressRequestPolicy(
                adapter_slug="rsshub",
                allowed_schemes=frozenset({"http"}),
            ),
        )


async def test_internal_resolution_cannot_escape_registered_network() -> None:
    registration = InternalServiceRegistration(
        identity="local-rsshub",
        adapter_slug="rsshub",
        scheme="http",
        hostname="rsshub.gni.internal",
        port=1200,
        address_networks=(ipaddress.ip_network("10.55.0.0/24"),),
        tls_policy="plaintext_internal",
        purpose="local RSSHub acquisition",
    )
    guard = OutboundEgressGuard(
        resolver=StaticResolver(
            {"rsshub.gni.internal": ("10.56.0.10",)}
        ),
        internal_services=InternalServiceRegistry((registration,)),
    )

    with pytest.raises(OutboundDestinationRejected, match="escaped"):
        await guard.validate(
            "http://rsshub.gni.internal:1200/feed",
            EgressRequestPolicy(
                adapter_slug="rsshub",
                allowed_schemes=frozenset({"http"}),
                internal_service_identity="local-rsshub",
            ),
        )
