# Phase 3 Proof 34 Owner Approval Decisions

**Approver:** GNI Owner<br>
**Approval date:** 08-24-2026<br>
**Decision:** Approved<br>
**Scope:** Proof 34 version-one robots policy defaults, validation bounds, parser distribution, and parser provenance<br>
**Implementation status:** Approved for implementation; implementation and acceptance evidence pending

## Decision

The GNI Owner approves the following version-one defaults for Proof 34:

```text
acquisition.robots.cache.max_age_seconds
    86400

acquisition.robots.cache.max_stale_seconds
    604800

acquisition.robots.fetch_limits
    max_response_bytes: 524288
    max_redirects: 5
    connect_timeout_seconds: 10
    read_timeout_seconds: 30

acquisition.robots.crawl_delay.enforce
    true
```

## Parser Distribution and Provenance

The approved version-one robots parser is:

```text
distribution
    protego==0.6.2

parser_name
    protego

parser_version
    0.6.2

source_commit
    efe5039d39ee51f117acd0b01ffd8109ae265c22

wheel_sha256
    714de21d82527c9be900066c3211b266985dd6a19b6e70c57e033fc1a589f3ff
```

The implementation must pin the exact distribution and verify the acquired
wheel against the approved SHA-256 value. Persisted parser provenance uses the
approved parser name and version. Source and wheel provenance must remain
traceable in supply-chain and acceptance evidence.

Approval selects the parser distribution and permits implementation. It does
not by itself establish that the installed artifact, decision-trace adapter,
or Crawl-delay behavior has passed Proof 34 acceptance testing.

## Version-One Validation Bounds

The Owner approves these closed ranges:

| Policy field | Minimum | Maximum | Default |
| --- | ---: | ---: | ---: |
| `acquisition.robots.cache.max_age_seconds` | 300 | 86400 | 86400 |
| `acquisition.robots.cache.max_stale_seconds` | 0 | 2592000 | 604800 |
| `acquisition.robots.fetch_limits.max_response_bytes` | 524288 | 2097152 | 524288 |
| `acquisition.robots.fetch_limits.max_redirects` | 5 | 10 | 5 |
| `acquisition.robots.fetch_limits.connect_timeout_seconds` | 1 | 30 | 10 |
| `acquisition.robots.fetch_limits.read_timeout_seconds` | 1 | 60 | 30 |

All values are integers. Boolean values are not accepted as integers. The
version-one fetch-limits object is closed and rejects missing or unknown
fields.

Scoped values may be more conservative than the approved defaults. No scoped
value may exceed installation-owned egress hard limits.

## Authority Boundary

These approvals resolve the six concrete default decisions and the parser
selection decision identified by the Proof 34 restart review. They also fix
the version-one Crawl-delay enforcement default.

The mediated-adapter architecture decision was subsequently resolved by
`PHASE_3_PROOF_34_MEDIATED_ROBOTS_AND_UI_OVERRIDE_DECISION.md`, approved on
08-24-2026.

## Completion Boundary

This record preserves the Owner's selected values; it does not grant or define
the Owner's authority. It does not claim that policy registration, persistence,
retrieval, parser integration, evaluation, gates, reconciliation, UI,
migrations, tests, runtime proof, or final Proof 34 acceptance are complete.
