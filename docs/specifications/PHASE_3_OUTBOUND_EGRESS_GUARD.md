# Phase 3 Outbound Egress Guard

Status: IMPLEMENTED CANDIDATE  
Date: 2026-07-30

## Scope

This package implements the shared outbound HTTP/HTTPS and SSRF boundary
required by the frozen Phase 3 Source Acquisition architecture. It introduces
no schema migration and does not activate an acquisition adapter.

Implemented:

- exact per-adapter HTTP/HTTPS scheme policy
- normalized IDNA hostname, port, URL-length, and user-info validation
- controlled asynchronous DNS resolution
- public rejection of loopback, private, link-local, multicast, unspecified,
  reserved, carrier-grade NAT, IPv4-mapped forbidden IPv6, cloud metadata,
  localhost, mDNS `.local`, and `home.arpa` targets
- rejection when any address in a mixed DNS answer is forbidden
- deterministic connection to the selected validated IP
- original hostname in the HTTP Host header and verified TLS SNI
- connected-peer extraction and exact comparison with the pinned IP
- fresh connection pooling for every redirect hop so SNI cannot cross origins
- redirect revalidation, bounded redirect count, and HTTPS downgrade refusal
- cross-origin removal of standard and adapter-declared credential headers
- cross-origin refusal of adapter-declared credential query parameters
- system public-CA verification with TLS 1.2 minimum and no environment proxy
- header, declared body, decoded streaming body, and total-duration limits
- redacted returned URLs and removal of standard secret-bearing response headers
- exact trusted installation registration for GNI-owned internal services

## DNS Rebinding and Connection Proof

Validation is not followed by a second hostname lookup in the HTTP transport.
For each hop:

```text
normalize hostname and port
        ↓
resolve and validate every answer
        ↓
select one validated address
        ↓
replace only the transport URL host with that IP
        ↓
send original Host header and TLS SNI
        ↓
read the socket peer and require exact equality with the selected IP
```

Redirects repeat the complete sequence. A private answer, mixed public/private
answer, changed peer, resolution failure, invalid peer proof, or forbidden
redirect fails closed.

## Credential Boundary

User-info is never accepted in a URL. Adapters declare every request header and
query key that carries credentials. Standard Authorization,
Proxy-Authorization, and Cookie headers are credential-bearing by default.

When origin changes, credential headers are removed permanently. A target URL
that contains a declared query credential is rejected instead of forwarded.
Returned requested/final URLs replace declared credential values with
`[REDACTED]`; Set-Cookie and standard authorization response headers are not
returned to callers.

No exception includes the requested URL, credential value, response body, or
provider-controlled header value.

## Internal Services

Private/local destinations have no endpoint-level bypass. Trusted worker
composition may supply an `InternalServiceRegistry`. Each registration binds:

```text
identity
exact adapter slug
exact scheme
normalized hostname
exact port
one or more parsed address networks
TLS policy
purpose
```

The request must name that identity and match every field. Every resolved
address must remain inside the registered networks. Without the identity,
ordinary public-address rules apply. Initial TLS policies support verified
public-CA HTTPS and explicitly registered plaintext internal HTTP; no
certificate-verification bypass exists.

Durable administration of installation registrations remains part of later
operator UI/worker composition. The adapter/secret/rate persistence candidate
is now implemented separately; Source and endpoint records still cannot
create trusted internal-service registrations.

## Deliberate Exclusions

This candidate does not complete:

- browser child-resource routing
- shared acquisition worker composition
- migration of the legacy RSS/Atom compatibility fetcher
- internal private-CA certificate registration
- production acquisition adapters or health UI
- formal Phase 3 implementation freeze

The legacy RSS/Atom path remains explicitly pre-cutover and must not claim this
guard until it moves into the shared acquisition worker.

## Proof Surface

Automated tests prove:

- direct IPv4, IPv6, mapped IPv6, metadata, CGNAT, and local-use rejection
- mixed public/private DNS refusal
- approved-scheme and user-info refusal
- IP-pinned transport URL with original Host and SNI
- connected-peer mismatch refusal
- DNS/SSRF validation on every redirect
- private redirect and HTTPS downgrade refusal
- cross-origin header stripping and query-credential refusal
- redirect, header, declared-byte, decoded-byte, and duration limits
- invalid Content-Length refusal
- redacted returned metadata
- exact internal-service authorization and address-containment refusal

A live production smoke proved public-CA TLS/SNI against `example.com` while
connecting to the validated peer address, followed by direct loopback refusal.
