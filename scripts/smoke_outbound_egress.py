from __future__ import annotations

import asyncio

from app.services.outbound_egress_service import (
    EgressRequestPolicy,
    GuardedHTTPClient,
    OutboundDestinationRejected,
)


async def _run() -> None:
    client = GuardedHTTPClient()
    policy = EgressRequestPolicy(
        adapter_slug="egress-smoke",
        allowed_schemes=frozenset({"https"}),
    )
    response = await client.get(
        "https://example.com/",
        policy=policy,
        headers={"User-Agent": "GNI-Egress-Smoke/1"},
    )
    if response.status_code != 200 or not response.content:
        raise RuntimeError("Public HTTPS egress smoke returned an invalid response.")

    try:
        await client.get(
            "https://127.0.0.1/",
            policy=policy,
        )
    except OutboundDestinationRejected:
        pass
    else:
        raise RuntimeError("Outbound guard did not reject loopback.")

    print(
        "outbound egress smoke passed: "
        f"status={response.status_code} "
        f"peer={response.connected_address} "
        f"bytes={response.response_bytes}"
    )


if __name__ == "__main__":
    asyncio.run(_run())
