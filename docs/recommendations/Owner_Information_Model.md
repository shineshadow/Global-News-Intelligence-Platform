

# Recommendation:

**Status:** Superseded
**Superseded:** 08-04-2026
**Superseded by:** `docs/recommendations/Reusable_Owner_Operation_Information_And_Policy_Decision_Context.md`

Recommendation for providing Owner with detailed information to make override decisions that adhere to `../specifications/OWNER_AUTHORITY_AND_CONFIGURATION_STANDARD.md`.

## Owner Information model

So the central relationship is:

run status = what happened to the execution
gate state = what currently prevents acquisition
reason code = precisely why
details = evidence needed to decide what to do

## A durable cross-GNI model 

Define it as a general **operation-result envelope**, with domain-specific reason codes. It should not be limited to acquisition errors or force inference concepts into acquisition gate slugs.

A durable cross-GNI model would look like:

```text
operation_domain
    acquisition | inspection | inference | classification |
    monitoring | alerting | calendar

operation_type
    retrieve_feed | inspect_artifact | infer_relationship | ...

execution_status
    queued | running | succeeded | partial | failed |
    delayed | blocked | skipped | cancelled

outcome_code
    domain-specific result

gate_state - what currently prevents progress
    none
    rate_limited
    robots_denied
    robots_delayed
    robots_unavailable
    policy_unavailable
    authentication_failed
    egress_blocked
    artifact_rejected
    inspection_unavailable
    storage_unavailable
    adapter_unavailable
    configuration_invalid

reason_code
    stable, namespaced machine-readable explanation

message
    sanitized owner-facing summary

details
    versioned, structured evidence

severity
    info | warning | error | critical

retryable
    true | false

next_eligible_at
     when retry or policy reevaluation may occur

provenance
    policy, adapter, model, ruleset, detector, and version identities

recommended_action
    optional owner guidance

override_evidence
    optional audited owner decision

owner_override
    override identity, scope, actor, and expiration when applicable

latest_run_status
    running | succeeded | partial | failed | delayed

started_at / finished_at
```

Namespaced reason codes prevent collisions:

```text
acquisition.robots_path_disallowed
inspection.archive_traversal_detected
inference.insufficient_evidence
inference.model_unavailable
classification.no_applicable_label
monitoring.no_match
alerting.delivery_rejected
```

The critical distinction is that execution success and domain outcome are independent.

I would apply three design rules:

1. Keep the common envelope stable, but let each domain own its valid outcome and reason-code vocabulary.
2. Preserve complete append-only result history; “latest” should only be a UI projection.
3. Use a common service/DTO and UI renderer, not necessarily one enormous polymorphic database table. Domain tables can retain their stronger constraints and specialized evidence.

With that adjustment, the model can support acquisition now and later inference, classification, monitoring, calendar resolution, and alert delivery without redesigning the owner-facing status system each time.

Successful runs can also need an outcome code, such as 'not_modified', 'verified_empty', or 'unchanged'.

The main goal is, I the owner, want to know whats happening and why with details. Not just a 'success' or 'error' or 'failed'. I want to know why with details because those details may cause me to intervine and override a default behavior.






