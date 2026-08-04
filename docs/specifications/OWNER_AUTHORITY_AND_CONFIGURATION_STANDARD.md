# Owner Authority and Configuration Standard

**Owner approval:** 2026-08-03  
**Status:** GOVERNING — IMPLEMENTED FOUNDATION  
**Database authority head:** `f6a8c2d4e901`

## Governing Rule

The owner of GNI has final authority over every runtime policy, safety
behavior, limit, format, schedule, workflow, and configuration. Safe defaults
are strongly preferred, but a default is not an irrevocable rule.

No architecture, implementation, migration, review, or AI-assisted change may
declare a policy non-configurable, non-bypassable, permanently read-only, or
outside owner control without the owner's explicit approval for that exact
restriction. Silence, prior AI-generated prose, and a commit authored under
the owner's Git identity do not establish that approval.

External systems and physical constraints remain factual. For example, an
owner override can authorize GNI to retry despite a provider limit, but cannot
force the provider to return content. GNI records both the external signal and
the owner's effective decision.

## Authority Surface

The primary authority is the PostgreSQL-backed `owner_policy_overrides` ledger.
It supports:

- JSON policy values rather than boolean-only bypasses;
- global, adapter, platform, credential, origin, Source, endpoint, and exact
  request scopes;
- exact-scope precedence, explicit priority, activation and expiration times;
- permanent, bounded-use, and single-use authority;
- actor, reason, and risk acknowledgement on creation;
- supersession and revocation without deleting history; and
- append-only creation, application, consumption, supersession, and revocation
  evidence.

The initial owner interface is deliberately operational rather than UI-bound:

```bash
python -m scripts.owner_policy set POLICY_KEY JSON_VALUE \
  --scope-type endpoint --scope-identity 47 \
  --actor shine \
  --reason "Owner-authorized behavior" \
  --acknowledge-risk "I accept responsibility for this policy change"

python -m scripts.owner_policy set POLICY_KEY false \
  --scope-type request --scope-identity REQUEST_ID \
  --once --actor shine --reason "One request" \
  --acknowledge-risk "I accept responsibility for this request"

python -m scripts.owner_policy effective POLICY_KEY --endpoint-id 47
python -m scripts.owner_policy list --active-only
python -m scripts.owner_policy history OVERRIDE_ID
python -m scripts.owner_policy revoke OVERRIDE_ID \
  --actor shine --reason "Override no longer required"
```

Database and script access remain installation-controlled. A future UI may
call the same service, but it may not create a second authority model.

## Precedence

Among matching owner policies, the most exact scope wins:

```text
exact request
endpoint
Source
origin
credential
platform
adapter
global
repository/application default
```

Priority resolves multiple equally exact matches. A more specific owner value
does not need to weaken a default; it may restore or strengthen it.

## Current Runtime Integration

The following policies are registered and consumed by the Phase 3 acquisition
worker:

```text
acquisition.robots.enforce                       default true
acquisition.retry_after.enforce                  default true
acquisition.provider_hard_limits.enforce         default true
acquisition.rate_limit.manual_poll_enforce       default true
acquisition.archive.inspection_limits             default bounded JSON object
```

Manual-poll authority bypasses local bucket denial while still creating an
atomic reservation and retaining counters. Retry-After and provider-limit
authority independently control whether observed external signals install or
govern durable holds. All provider observations remain persisted with the
effective owner-policy evidence.

Robots holds have their own durable bucket dimension and are evaluated through
`acquisition.robots.enforce`. Robots retrieval and parsing are not yet
implemented, so this is an authority integration point rather than a claim
that robots proof 34 is complete.

Archive inspection resolves the complete member/depth/expanded-byte/ratio/path
limit object before retrieval. The shared worker validates the exact field set
and positive integer values, consumes bounded-use authority, and passes the
effective policy plus audit evidence into the recursive sandbox runtime. See
`PHASE_3_ARCHIVE_TREE_INSPECTION_AND_PROMOTION.md`.

## Implementation Requirement

Adding a default is incomplete until its owner-control disposition is stated:

```text
policy key
value type and validation
default
supported scopes
resolution point
restart requirement
external consequences
audit evidence
default-path test
override-path test
```

If a control has not yet been connected to the owner service, documentation
must say so. It may not be described as permanently inaccessible merely because
the wiring remains incomplete.

## Data and Audit

Audit history is append-only by default so owner decisions remain explainable.
This is a protective implementation default, not a claim that the project
owner lacks database or code authority. Destructive owner operations, if
added, must distinguish intentionally rewriting/deleting history from ordinary
configuration so their consequences are unmistakable.

## Review Rule

Implementation reviews must test both:

1. the safe/default behavior; and
2. at least one exact, audited owner override for every integrated policy
   family.

Reviews must also compare new `cannot`, `never`, `non-configurable`, hard-limit,
and read-only language against this standard. Unapproved contradictions block
the review rather than owner authority.

## Verification

```text
focused owner-authority migration/service/worker suite       24 passed
guarded migration-safety suite                               23 passed
guarded non-migration repository suite                      401 passed
final owner-policy/worker hardening suite                    16 passed
current non-migration repository collection              402 collected
Alembic current                                  f6a8c2d4e901 (head)
Alembic schema drift                                         none
initial /var inode use                                        16%
post-migration /var inode use                                 18%
final /var inode use                                          56%
post-focused /var inode use                                   57%
```
