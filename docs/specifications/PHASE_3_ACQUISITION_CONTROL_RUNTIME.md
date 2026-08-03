# Phase 3 Acquisition Control Runtime

Status: IMPLEMENTED CANDIDATE  
Date: 2026-07-31

## Scope

This package implements the PostgreSQL-authoritative control plane required
before Phase 3 acquisition adapters can be activated:

- versioned adapter registry and exact endpoint compatibility tuples
- terminal Artifact Format capability and required secret-slot declarations
- versioned typed endpoint configuration with no legacy endpoint backfill
- durable endpoint leases, heartbeats, replay identity, expiry, takeover, and
  append-only lease events
- global secret references and explicit endpoint, Source, platform-account,
  or installation bindings without persisted secret values
- environment, systemd credential, and injected external-store resolution
- hierarchical installation, adapter, platform, credential, origin, Source,
  and endpoint rate policy
- atomic all-bucket request reservations, concurrency recovery, provider
  holds, and append-only observations

The migration activates no adapter, creates no secret reference, and adopts no
historical endpoint. It seeds only the frozen conservative installation rate
policy and its empty runtime bucket.

## Fail-Closed Request Authority

An endpoint is eligible only when its exact type, format, acquisition method,
and optional platform tuple is declared by an active adapter. Active
configuration also requires an identifiable and safely parseable terminal
Artifact Format.

Required adapter secret slots are resolved by explicit binding precedence:

```text
endpoint → Source → platform account → installation
```

Missing, invalid, expired, disabled, or unavailable required secrets raise
before an adapter receives request credentials. Values exist only in the
worker's in-memory result and are absent from PostgreSQL, events, errors, and
rate identities.

Every request must reserve all applicable durable buckets in one short
transaction. Buckets are locked in deterministic order. Any hold, quota,
spacing, concurrency, or policy failure creates no reservation and changes no
request counters. PostgreSQL unavailability therefore cannot yield request
authority; Redis is not involved.

## Durable Idempotency

Lease identity is endpoint-scoped and includes the configuration version.
Scheduled execution uses the normalized schedule window; manual execution uses
an explicit idempotency key. One active lease may exist per endpoint.

The database serializes acquisition through an endpoint advisory transaction
lock and partial unique constraint. Repeating an execution identity is a
replay. A different execution is busy until the active lease expires, after
which takeover expires the old lease and appends both expiry and takeover
evidence transactionally.

## Database Enforcement

PostgreSQL triggers independently reject:

- endpoint configurations whose exact tuple is not registered
- active configurations backed by inactive adapters
- recursively secret-bearing endpoint configuration keys
- mismatched adapter secret slots, authentication types, or binding scopes
- malformed exact rate scope identities
- credential buckets not tied to their exact `secret_reference_id`
- leases not tied to the endpoint's exact active configuration version
- mutation or deletion of append-only control evidence

Downgrade is lossless-only. It succeeds only when no acquisition-control state
exists and the sole installation policy, binding, and bucket still match the
untouched migration seed. Otherwise it refuses without deleting state.

## Deliberate Exclusions

This candidate does not implement production acquisition adapters, the shared
worker composition, legacy RSS migration, expanded endpoint health, operator
administration UI, or the formal Phase 3 implementation freeze. Those remain
later packages.

## Proof Surface

Automated tests directly cover:

- clean downgrade/re-upgrade and zero schema drift
- no endpoint or secret backfill
- lossless downgrade refusal with acquisition-owned state
- exact adapter activation and endpoint configuration
- lease acquisition, replay, busy refusal, expiry, and takeover
- required-secret failure before outbound request authority
- database unavailability yielding no outbound request authority
- simultaneous all-bucket authorization with exactly one complete reservation
- no partial reservation or counter mutation on denial
- database rejection of recursively secret-bearing configuration
