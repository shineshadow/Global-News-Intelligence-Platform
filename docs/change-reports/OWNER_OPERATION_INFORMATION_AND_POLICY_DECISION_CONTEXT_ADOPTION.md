# Owner Operation Information and Policy Decision Context Adoption

**Approver:** GNI Owner
**Approval date:** 08-04-2026
**Decision:** Approved
**Scope:** Combined owner-operation information model, owner-policy decision context, and Proof 34 implementation direction
**Disposition:** The consolidated recommendation supersedes the two earlier recommendations
**Implementation status:** Not yet implemented

## Decision

The GNI Owner approves the combined recommendation establishing a reusable Owner Operation Information Model and Owner Policy Decision Context for the Global News Intelligence Platform.

The approved recommendation incorporates the compatible and related requirements from:

* `Owner_Information_Model.md`
* `Reusable_Owner_Policy_Decision_Context_And_Information_Layer.md`

The consolidated recommendation supersedes both earlier documents as the controlling recommendation.

## Approved Direction

GNI shall provide the Owner with sufficient structured information to determine:

* what operation GNI attempted;
* what happened during execution;
* what domain result was produced;
* what currently prevents progress;
* precisely why the result or gate occurred;
* what evidence produced the decision;
* what policy controlled the runtime behavior;
* whether an Owner override applied;
* what scope and duration govern an override;
* what an available override would change;
* what external evidence remains true despite an override;
* whether and when GNI may attempt the operation again.

The common owner-facing information contract shall distinguish execution status, domain outcome, gate state, reason code, structured details, provenance, retry eligibility, policy resolution, override evidence, and effective runtime decision.

Complete result and decision history shall be retained. A latest-state view is a projection and shall not replace authoritative historical records.

Domain implementations may retain specialized persistence and constraints. The common information model does not require one universal polymorphic database table.

## Initial Implementation

Robots acquisition and enforcement under Phase 3 proof 34 shall be the first complete implementation of the approved model.

The proof shall include robots evidence, robots evaluation, gate state, reason code, owner-policy resolution, effective enforcement decision, override evidence, next eligibility, path isolation, history preservation, and owner-facing decision information.

## Supersession

The following recommendations are retained as historical records and marked Superseded:

* `Owner_Information_Model.md`
* `Reusable_Owner_Policy_Decision_Context_And_Information_Layer.md`

The controlling recommendation is:

`docs/recommendations/Reusable_Owner_Operation_Information_And_Policy_Decision_Context.md`

## Implementation Status

This adoption approves the architecture and implementation direction. It does not claim that the specifications, database changes, services, UI components, tests, or proof 34 implementation are complete.

Implementation completion requires approved normative specifications, passing tests, required governance records, runtime proof, and acceptance evidence.

