from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Protocol

RelationshipFamily = Literal[
    "event_geography",
    "event_topic",
    "event_entity",
    "event_source",
]
RelationshipActor = Literal["system", "internal_agent", "external_model"]
EvidenceUseKind = Literal["supports", "contradicts", "corrects"]

ROLE_VOCABULARIES: dict[RelationshipFamily, frozenset[str]] = {
    "event_geography": frozenset(
        {"venue", "jurisdiction", "affected_area", "participant_location"}
    ),
    "event_topic": frozenset({"primary", "secondary"}),
    "event_entity": frozenset(
        {"organizer", "participant", "subject", "speaker", "host"}
    ),
    "event_source": frozenset({"official", "expected", "reference"}),
}


@dataclass(frozen=True)
class CalendarExtractionEvidence:
    id: int
    evidence_kind: str
    confidence: Decimal
    authority_score: Decimal
    fingerprint: str
    source_id: int | None
    document_id: int | None
    document_source_id: int | None = None
    document_topics: tuple[CalendarDocumentTopic, ...] = ()


@dataclass(frozen=True)
class CalendarDocumentTopic:
    topic_id: int
    confidence: Decimal
    classification_method: str
    classifier_version: str | None
    classification_run_id: int | None


@dataclass(frozen=True)
class CalendarRelationshipEvidenceUse:
    evidence_id: int
    use_kind: EvidenceUseKind = "supports"


@dataclass(frozen=True)
class CalendarRelationshipCandidate:
    family: RelationshipFamily
    target_id: int
    role: str
    confidence: Decimal
    assignment_method: str
    actor_kind: RelationshipActor
    evidence_uses: tuple[CalendarRelationshipEvidenceUse, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.target_id <= 0:
            raise ValueError("Relationship candidate target ID must be positive.")
        if self.role not in ROLE_VOCABULARIES[self.family]:
            raise ValueError(
                f"Role {self.role!r} is invalid for {self.family}."
            )
        if self.confidence < 0 or self.confidence > 1:
            raise ValueError(
                "Relationship candidate confidence must be between zero and one."
            )
        if not self.evidence_uses:
            raise ValueError(
                "Relationship candidates require normalized evidence."
            )
        evidence_ids = [use.evidence_id for use in self.evidence_uses]
        if any(evidence_id <= 0 for evidence_id in evidence_ids):
            raise ValueError("Relationship evidence IDs must be positive.")
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError(
                "Relationship candidate evidence IDs must be distinct."
            )


@dataclass(frozen=True)
class CalendarRelationshipExtractionContext:
    event_id: int
    occurrence_id: int | None
    inference_run_id: int
    evidence_snapshot_hash: str
    evidence: tuple[CalendarExtractionEvidence, ...]


class CalendarRelationshipExtractionAdapter(Protocol):
    async def extract(
        self,
        context: CalendarRelationshipExtractionContext,
    ) -> tuple[CalendarRelationshipCandidate, ...]: ...


def _fuse_confidence(values: list[Decimal]) -> Decimal:
    remaining = Decimal(1)
    for value in values:
        remaining *= Decimal(1) - value
    return (Decimal(1) - remaining).quantize(Decimal("0.0001"))


class RepositoryCalendarRelationshipExtractionAdapter:
    """Extract only relationships explicitly supported by normalized records."""

    async def extract(
        self,
        context: CalendarRelationshipExtractionContext,
    ) -> tuple[CalendarRelationshipCandidate, ...]:
        if context.occurrence_id is not None:
            return ()

        grouped: dict[
            tuple[RelationshipFamily, int, str],
            list[tuple[Decimal, int, dict[str, Any]]],
        ] = {}
        for evidence in context.evidence:
            if evidence.evidence_kind == "contradicts":
                continue
            source_id = evidence.source_id or evidence.document_source_id
            if source_id is not None:
                grouped.setdefault(
                    ("event_source", source_id, "reference"),
                    [],
                ).append(
                    (
                        evidence.confidence,
                        evidence.id,
                        {
                            "derivation": "normalized_evidence_source",
                            "document_id": evidence.document_id,
                        },
                    )
                )
            for topic in evidence.document_topics:
                confidence = evidence.confidence * topic.confidence
                grouped.setdefault(
                    ("event_topic", topic.topic_id, "secondary"),
                    [],
                ).append(
                    (
                        confidence,
                        evidence.id,
                        {
                            "derivation": "active_document_topic",
                            "document_id": evidence.document_id,
                            "document_classification_method": (
                                topic.classification_method
                            ),
                            "document_classifier_version": (
                                topic.classifier_version
                            ),
                            "document_classification_run_id": (
                                topic.classification_run_id
                            ),
                        },
                    )
                )

        candidates: list[CalendarRelationshipCandidate] = []
        for (family, target_id, role), observations in sorted(
            grouped.items()
        ):
            uses = tuple(
                CalendarRelationshipEvidenceUse(evidence_id=evidence_id)
                for evidence_id in sorted(
                    {observation[1] for observation in observations}
                )
            )
            candidates.append(
                CalendarRelationshipCandidate(
                    family=family,
                    target_id=target_id,
                    role=role,
                    confidence=_fuse_confidence(
                        [observation[0] for observation in observations]
                    ),
                    assignment_method="rule",
                    actor_kind="system",
                    evidence_uses=uses,
                    provenance={
                        "adapter": "repository-structured-extraction",
                        "adapter_version": "1",
                        "observations": [
                            observation[2] for observation in observations
                        ],
                        "negative_guards": [
                            "no_source_country_to_event_geography",
                            "no_entity_ancestry_to_event_geography",
                            "no_document_entity_role_promotion",
                        ],
                    },
                )
            )
        return tuple(candidates)
