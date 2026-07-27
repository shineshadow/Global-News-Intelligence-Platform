from dataclasses import dataclass, field
from typing import Any, Literal


ClassificationMethod = Literal[
    "deterministic_rule",
    "source_default",
    "endpoint_default",
    "metadata_mapping",
]


@dataclass(slots=True, frozen=True)
class TopicCandidate:
    slug: str
    confidence: float
    relationship_role: str
    classification_method: ClassificationMethod
    classifier_version: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class GeographyCandidate:
    slug: str
    confidence: float
    relationship_role: str
    classification_method: ClassificationMethod
    classifier_version: str
    taxonomy_version: str = "1.0"
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DocumentTypeCandidate:
    slug: str
    confidence: float
    is_primary: bool
    classification_method: ClassificationMethod
    classifier_version: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EntityCandidate:
    entity_id: int
    confidence: float
    entity_role: str
    classification_method: ClassificationMethod
    classifier_version: str
    mention_text: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class DeterministicClassificationResult:
    topics: tuple[TopicCandidate, ...] = ()
    geographies: tuple[GeographyCandidate, ...] = ()
    entities: tuple[EntityCandidate, ...] = ()
    document_types: tuple[DocumentTypeCandidate, ...] = ()
