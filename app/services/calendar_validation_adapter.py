from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Protocol

from app.services.exceptions import ServiceUnavailableError

INTERNAL_EVIDENCE_STRATEGY = "evidence-reconciliation"
INTERNAL_EVIDENCE_STRATEGY_VERSION = "1"
INTERNAL_ADVERSARIAL_STRATEGY = "adversarial-canonical-review"
INTERNAL_ADVERSARIAL_STRATEGY_VERSION = "1"


@dataclass(frozen=True)
class CalendarEvidenceFact:
    id: int
    evidence_kind: str
    confidence: Decimal
    authority_score: Decimal
    fingerprint: str


@dataclass(frozen=True)
class CalendarAssertionCandidate:
    id: int
    validation_state: str
    confidence: Decimal


@dataclass(frozen=True)
class CalendarResolutionContext:
    event_id: int
    occurrence_id: int | None
    conflict_id: int
    evidence_snapshot_hash: str
    assertions: tuple[CalendarAssertionCandidate, ...]
    evidence: tuple[CalendarEvidenceFact, ...]


@dataclass(frozen=True)
class CalendarResolutionDecision:
    outcome: Literal["resolved", "unresolved"]
    selected_assertion_id: int | None = None
    confidence: Decimal = Decimal(0)
    rationale: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome == "resolved" and self.selected_assertion_id is None:
            raise ValueError("A resolved decision requires an assertion.")
        if self.outcome == "unresolved" and self.selected_assertion_id is not None:
            raise ValueError("An unresolved decision cannot select an assertion.")
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError("Decision confidence must be between zero and one.")


@dataclass(frozen=True)
class CalendarExternalRoutingResult:
    status: Literal["completed", "failed", "unavailable", "ineligible"]
    router_decision_id: str
    decision: CalendarResolutionDecision | None = None
    provider: str | None = None
    model: str | None = None
    model_version: str | None = None
    failure_code: str | None = None
    failure_detail: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status == "completed":
            if self.decision is None or self.provider is None or self.model is None:
                raise ValueError(
                    "Completed external routing requires a decision, provider, and model."
                )
        elif self.decision is not None:
            raise ValueError("An incomplete external route cannot return a decision.")
        if self.status != "completed" and not self.failure_code:
            raise ValueError("An incomplete external route requires a failure code.")


class CalendarValidationAdapter(Protocol):
    async def resolve(
        self,
        context: CalendarResolutionContext,
        *,
        strategy: str,
        strategy_version: str,
    ) -> CalendarResolutionDecision: ...


class CalendarExternalRouter(Protocol):
    async def adjudicate(
        self,
        context: CalendarResolutionContext,
    ) -> CalendarExternalRoutingResult: ...


def _evidence_strength(
    evidence: tuple[CalendarEvidenceFact, ...],
    kinds: set[str],
) -> Decimal:
    remaining = Decimal(1)
    for fact in evidence:
        if fact.evidence_kind not in kinds:
            continue
        weight = fact.confidence * (
            Decimal("0.5") + Decimal("0.5") * fact.authority_score
        )
        remaining *= Decimal(1) - weight
    return (Decimal(1) - remaining).quantize(Decimal("0.0001"))


class DeterministicCalendarValidationAdapter:
    """Provider-neutral internal reasoning with two distinct strategies."""

    async def resolve(
        self,
        context: CalendarResolutionContext,
        *,
        strategy: str,
        strategy_version: str,
    ) -> CalendarResolutionDecision:
        if strategy_version != "1":
            raise ServiceUnavailableError(
                f"Unsupported Calendar strategy version {strategy_version}."
            )

        support = _evidence_strength(
            context.evidence,
            {"supports", "corrects"},
        )
        contradiction = _evidence_strength(
            context.evidence,
            {"contradicts"},
        )
        candidates = {
            candidate.validation_state: candidate
            for candidate in context.assertions
        }

        if strategy == INTERNAL_EVIDENCE_STRATEGY:
            margin = abs(support - contradiction)
            selected_state = "probable" if support > contradiction else "rejected"
            candidate = candidates.get(selected_state)
            if candidate is not None and margin >= Decimal("0.35"):
                return CalendarResolutionDecision(
                    outcome="resolved",
                    selected_assertion_id=candidate.id,
                    confidence=margin,
                    rationale={
                        "strategy": "evidence_reconciliation",
                        "support_strength": str(support),
                        "contradiction_strength": str(contradiction),
                        "decision_rule": "minimum_margin_0.35",
                    },
                )
            return CalendarResolutionDecision(
                outcome="unresolved",
                confidence=margin,
                rationale={
                    "strategy": "evidence_reconciliation",
                    "support_strength": str(support),
                    "contradiction_strength": str(contradiction),
                    "reason": "evidence_margin_below_resolution_threshold",
                },
            )

        if strategy == INTERNAL_ADVERSARIAL_STRATEGY:
            weakest_side = min(support, contradiction)
            strongest_side = max(support, contradiction)
            dominance = strongest_side - weakest_side
            selected_state = "probable" if support > contradiction else "rejected"
            candidate = candidates.get(selected_state)
            if (
                candidate is not None
                and weakest_side < Decimal("0.20")
                and dominance >= Decimal("0.50")
            ):
                return CalendarResolutionDecision(
                    outcome="resolved",
                    selected_assertion_id=candidate.id,
                    confidence=dominance,
                    rationale={
                        "strategy": "adversarial_canonical_review",
                        "support_strength": str(support),
                        "contradiction_strength": str(contradiction),
                        "decision_rule": "weak_opposition_and_dominance",
                        "canonical_constraints_reapplied": True,
                    },
                )
            return CalendarResolutionDecision(
                outcome="unresolved",
                confidence=dominance,
                rationale={
                    "strategy": "adversarial_canonical_review",
                    "support_strength": str(support),
                    "contradiction_strength": str(contradiction),
                    "challenged_first_conclusion": True,
                    "canonical_constraints_reapplied": True,
                    "reason": "material_opposition_survived_critical_review",
                },
            )

        raise ServiceUnavailableError(f"Unknown Calendar strategy {strategy}.")


class DisabledCalendarExternalRouter:
    """Default installation policy: no external provider is configured."""

    async def adjudicate(
        self,
        context: CalendarResolutionContext,
    ) -> CalendarExternalRoutingResult:
        return CalendarExternalRoutingResult(
            status="ineligible",
            router_decision_id=(
                f"calendar-validation:external-disabled:{context.conflict_id}"
            ),
            failure_code="external_provider_not_configured",
            failure_detail=(
                "No external calendar_validation route is configured for this "
                "installation."
            ),
            provenance={
                "task": "calendar_validation",
                "egress_permitted": False,
                "policy_scope": "installation",
            },
        )
