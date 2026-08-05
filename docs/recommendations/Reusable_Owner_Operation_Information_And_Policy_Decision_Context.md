## Recommendation

**Approver:** GNI Owner
**Approval date:** 08-04-2026
**Decision:** Approved
**Scope:** Combined owner-operation information model, owner-policy decision context, and Proof 34 implementation direction
**Disposition:** The consolidated recommendation supersedes the two earlier recommendations
**Implementation status:** Not yet implemented

**Supersedes:**
- Owner_Information_Model.md
- Reusable_Owner_Policy_Decision_Context_And_Information_Layer.md

## 1. Owner Operation Information Model

Preserve Codex’s central relationship:
```text
execution status = what happened
outcome code = what result was produced
gate state = what currently prevents progress
reason code = precisely why
details = evidence needed to understand and decide
```

This becomes the reusable cross-GNI model for acquisition, inspection, inference, classification, monitoring, alerting, and calendar operations.

## 2. Owner Policy Decision Context

Preserve the policy-specific information from my earlier recommendation:
```text
external observation
applicable policy candidates
selected controlling policy
default policy value
effective policy value
override identity
override scope
actor and reason
risk acknowledgement
validity and remaining uses
effective runtime decision
impact of a proposed override
```

This explains not only what happened, but how owner authority affected—or could affect—the result.

## 3. Proof 34 Implementation Slice

Use robots acquisition and enforcement as the first implementation of both layers:
```text
robots evidence
robots evaluation
execution result
current gate
reason code
policy resolution
effective enforcement decision
override evidence
next eligibility
owner intervention options
complete append-only history
```

## 4. Combined Concepts

This recommendation incorporates the compatible and related requirements from both earlier recommendations that this recommendation supersedes, including:
```text
- the cross-GNI operation-result envelope;
- domain-owned outcome and reason vocabularies;
- append-only result history;
- versioned structured evidence;
- external observations;
- owner-policy resolution;
- controlling override identity and scope;
- override impact preview;
- effective runtime decision;
- Proof 34 as the first implementation slice.
```

## 5. Once the consolidated recommendation is approved 

It should lead to separate normative specifications rather than remain the permanent authority itself:
```text
docs/specifications/OWNER_OPERATION_INFORMATION_MODEL.md

docs/specifications/OWNER_POLICY_DECISION_CONTEXT_STANDARD.md

docs/specifications/ROBOTS_ACQUISITION_AND_ENFORCEMENT_STANDARD.md
```






























