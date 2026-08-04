# Owner Configuration Lockout Inventory

**Audit date:** 2026-08-03  
**Status:** ACTIVE REMEDIATION INVENTORY

This inventory records policy areas previously described or implemented as
unavailable to the owner. The Owner Authority and Configuration Standard
supersedes those blanket restrictions. “Pending” means the safe default still
operates and an owner-policy adapter must be added; it does not mean the owner
approved a permanent lockout.

| Policy family | Current default | Owner authority status | Next integration |
|---|---|---|---|
| Robots access/crawl decision | Enforce observed restriction | Registered and rate path wired; retrieval/parser pending | Fetch and parse robots evidence, then test allow, deny, and override |
| HTTP Retry-After | Honor bounded valid value | Implemented | Extend effective-policy diagnostics/UI if desired |
| Provider quota/reset and HTTP 429 fallback | Enforce provider hold | Implemented | Extend effective-policy diagnostics/UI if desired |
| Manual-poll rate denial | Same buckets as scheduled work | Implemented | Extend effective-policy diagnostics/UI if desired |
| Rate, burst, concurrency, spacing, retry, and daily budget values | Versioned database policy | Existing scoped policy tables; generic owner JSON value supported but field adapters pending | Route individual numeric values through owner resolution |
| Artifact rejection action | Delete rejected bytes | Pending | Add delete/quarantine/retain owner policy before Artifact finalization |
| Rejected-payload retention/restoration | No retention or restoration | Pending | Add protected quarantine/retention backend and explicit destructive-risk acknowledgement |
| Scanner requirement/unavailability | Mandatory and fail closed | Pending | Add scanner-required and unavailable-action policies |
| Sandbox limits and detector availability | Fixed limits and fail closed | Pending | Add bounded resource/action policy adapters |
| SSRF/private/internal destination policy | Public-only except installation registrations | Pending | Add exact owner network/host authorization without weakening destination evidence |
| Redirect credential forwarding | Strip/deny across origins | Pending | Add exact destination/credential authorization policy |
| Response byte/header/redirect/time limits | Installation-owned fixed limits | Pending | Route limit values through scoped owner policy |
| Missing/invalid secret behavior | Send no request | Pending | Add explicit fallback behavior policy without persisting secret values |
| Adapter/legacy fallback | Fail closed for configured Phase 3 endpoint | Pending | Add exact fallback and degraded-operation policies |
| Signature/hash/scanner bypass behavior | Always rescan known bytes | Pending | Add explicit owner acceptance path with provenance |
| Later signature authority release | Repository bootstrap only | Pending formal proof | Add owner-controlled release candidate lifecycle |
| Archive limits and all-or-nothing handling | Not implemented | Pending formal proofs | Include owner-configurable member/depth/ratio/action values |
| Canonical Artifact/history mutability | Append-only | Pending destructive-operation design | Provide explicit owner maintenance tooling distinct from ordinary mutation |
| Migration downgrade refusal | Lossless-only | Pending | Add owner-authorized destructive downgrade tooling with backup/evidence requirements |
| Cutover cohort size | Environment value, default one | Configurable through installation environment | Surface effective value and consider database owner policy |
| Date/time display format | American User-local standard | Pending project-wide preference authority | Replace universal formatting mandate with owner/user preference configuration |
| UI visibility and administrative controls | Several operational outcomes read-only | Pending | Route mutations through owner-authorized services; UI remains optional |
| Celery schedules and dispatch limits | Environment-backed defaults | Configurable through installation environment | Inventory restart requirements and optionally bridge to owner policies |
| Internal service identities | Installation environment registration | Configurable through installation environment | Add owner diagnostics and controlled runtime reload if desired |
| Artifact staging/canonical roots | Installation environment paths | Configurable through installation environment | Document restart and permission requirements |

## Repository Audit Rule

Future audits search specifications and runtime code for at least:

```text
non-configurable
non-bypassable
cannot override / cannot bypass / cannot ignore
must not / never
hard limit
read-only
fail closed
```

Each result must be classified as an external fact, a safe default, an
implemented owner policy, pending owner-policy wiring, or an explicitly
owner-approved invariant. The inventory is updated whenever a pending family
is wired or a new restriction is proposed.
