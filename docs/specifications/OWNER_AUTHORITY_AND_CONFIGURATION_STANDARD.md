# Owner Authority and Configuration Standard

**Owner approval:** 2026-08-03  
**Status:** GOVERNING — IMPLEMENTED FOUNDATION  
**Database authority head:** `f6a8c2d4e901`

## Governing Rule

The Owner of GNI has final authority over every runtime policy, safety
behavior, limit, format, schedule, workflow, and configuration. A default is not an irrevocable rule.

No architecture, implementation, migration, review, or AI-assisted change may
declare a policy non-configurable, non-bypassable, permanently read-only, or
outside Owner control without the Owner's explicit approval for that exact
restriction. Silence, prior AI-generated prose, and a commit authored under
the Owner's Git identity do not establish that approval.

## Authority Surface

The primary authority is the PostgreSQL-backed `Owner_policy_overrides` ledger.
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

```bash
python -m scripts.Owner_policy set POLICY_KEY JSON_VALUE \
  --scope-type endpoint --scope-identity 47 \
  --actor shine \
  --reason "Owner-authorized behavior" \
  --acknowledge-risk "I accept responsibility for this policy change"

python -m scripts.Owner_policy set POLICY_KEY false \
  --scope-type request --scope-identity REQUEST_ID \
  --once --actor shine --reason "One request" \
  --acknowledge-risk "I accept responsibility for this request"

python -m scripts.Owner_policy effective POLICY_KEY --endpoint-id 47
python -m scripts.Owner_policy list --active-only
python -m scripts.Owner_policy history OVERRIDE_ID
python -m scripts.Owner_policy revoke OVERRIDE_ID \
  --actor shine --reason "Override no longer required"
```

Database and script access remain installation-controlled. The installation is owned and controlled by the Owner. Therefore, the Database and script access ultimitly remain Owner-controlled. A future UI may call the same service, but it may not create a second authority model.

Owner information access is not created by a UI role or screen. Information
defined by a governing standard as Owner information shall remain available
through the implemented operational surface and shall be carried forward into
the designated Owner/Admin UI when that surface is built. An internal service,
worker, diagnostic, or authorized agent use of the same information does not
make it internal-only. Missing UI presentation is an implementation gap, not
an Owner-information lockout.

## Internal And Owner Information

Information may serve both internal operation and Owner explanation. A field used by workers, diagnostics, or authorized agent models is not therefore internal-only. When a domain standard marks information as Owner information:

```text
the authoritative structured value must be retained
the implemented operational/API/CLI surface must preserve Owner access
the future Admin UI must expose the registered Owner-visible projection
the User UI may omit administrative diagnostic detail
Admin-UI placement does not create or limit the Owner's information rights to it or Authority of it
missing UI presentation remains an explicit implementation gap
```

## Required Owner-Facing Presentation

A detail view shall answer:

```text
What was GNI trying to do?
What happened?
Who's at fault
What result was produced?
What currently blocks progress?
Why exactly did that happen?
What evidence produced that conclusion?
Which adapter, policy, ruleset, parser, detector, or model was used?
What action is available?
```

## Precedence

Among matching Owner policies, the most exact scope wins:

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

Priority resolves multiple equally exact matches.

## Current Runtime Integration

The following policies are registered and consumed by the Phase 3 acquisition
worker:

```text
acquisition.retry_after.enforce                  default true
acquisition.provider_hard_limits.enforce         default true
acquisition.rate_limit.manual_poll_enforce       default true
acquisition.archive.inspection_limits            default bounded JSON object
```

Manual-poll authority bypasses local bucket denial while still creating an
atomic reservation and retaining counters. Retry-After and provider-limit
authority independently control whether observed external signals install or
govern durable holds. All provider observations remain persisted with the
effective Owner-policy evidence.

Archive inspection resolves the complete member/depth/expanded-byte/ratio/path
limit object before retrieval. The shared worker validates the exact field set
and positive integer values, consumes bounded-use authority, and passes the
effective policy plus audit evidence into the recursive sandbox runtime. See
`PHASE_3_ARCHIVE_TREE_INSPECTION_AND_PROMOTION.md`.

## Implementation Requirement

Adding a default is incomplete until its Owner-control disposition is stated:

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

If a control has not yet been connected to the Owner service, documentation
must say so. It may not be described as permanently inaccessible merely because
the wiring remains incomplete.

## Data and Audit

Audit history is append-only by default so Owner decisions remain explainable.
This is an informative implementation meassure so the Owner has review capabilitites.

## Review Rule

Implementation reviews must test both:

1. the default behavior; and
2. at least one exact, audited Owner override for every integrated policy
   family.

Reviews must also compare new `cannot`, `never`, `non-configurable`, hard-limit,
and read-only language against this standard. Unapproved contradictions block
the review rather than Owner authority.

## Verification

```text
focused Owner-authority migration/service/worker suite       24 passed
guarded migration-safety suite                               23 passed
guarded non-migration repository suite                      401 passed
final Owner-policy/worker hardening suite                    16 passed
current non-migration repository collection              402 collected
Alembic current                                  f6a8c2d4e901 (head)
Alembic schema drift                                         none
initial /var inode use                                        16%
post-migration /var inode use                                 18%
final /var inode use                                          56%
post-focused /var inode use                                   57%
```
