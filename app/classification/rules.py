import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.classification.normalization import normalize_match_text
from app.classification.types import (
    DeterministicClassificationResult,
    DocumentTypeCandidate,
    TopicCandidate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULESET_PATH = (
    PROJECT_ROOT
    / "config"
    / "classification"
    / "deterministic_rules_v1.json"
)

RULE_CLASSIFIER_VERSION = "deterministic-rules-v1"


@dataclass(slots=True, frozen=True)
class MetadataTopicMapping:
    terms: tuple[str, ...]
    topic_slug: str
    confidence: float


@dataclass(slots=True, frozen=True)
class TopicKeywordRule:
    rule_id: str
    topic_slug: str
    confidence: float
    relationship_role: str
    fields: tuple[str, ...]
    any_terms: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class DocumentTypeKeywordRule:
    rule_id: str
    document_type_slug: str
    confidence: float
    fields: tuple[str, ...]
    any_terms: tuple[str, ...]


@dataclass(slots=True, frozen=True)
class DeterministicRuleSet:
    ruleset_version: str
    taxonomy_version: str
    metadata_topic_mappings: tuple[MetadataTopicMapping, ...]
    topic_keyword_rules: tuple[TopicKeywordRule, ...]
    document_type_keyword_rules: tuple[DocumentTypeKeywordRule, ...]

    def classify(
        self,
        *,
        title: str,
        summary: str | None,
        content: str | None,
        canonical_url: str | None,
        document_metadata: dict[str, Any] | None,
    ) -> DeterministicClassificationResult:
        fields = {
            "title": normalize_match_text(title),
            "summary": normalize_match_text(summary),
            "content": normalize_match_text(content),
            "url": normalize_match_text(canonical_url),
        }

        topics: list[TopicCandidate] = []
        document_types: list[DocumentTypeCandidate] = []

        topics.extend(
            self._classify_metadata_topics(
                document_metadata or {},
            )
        )

        for rule in self.topic_keyword_rules:
            matched = _first_matching_term(
                fields,
                rule.fields,
                rule.any_terms,
            )
            if matched is None:
                continue

            topics.append(
                TopicCandidate(
                    slug=rule.topic_slug,
                    confidence=rule.confidence,
                    relationship_role=rule.relationship_role,
                    classification_method="deterministic_rule",
                    classifier_version=RULE_CLASSIFIER_VERSION,
                    evidence={
                        "rule_id": rule.rule_id,
                        "matched_term": matched,
                        "matched_fields": list(rule.fields),
                    },
                )
            )

        for rule in self.document_type_keyword_rules:
            matched = _first_matching_term(
                fields,
                rule.fields,
                rule.any_terms,
            )
            if matched is None:
                continue

            document_types.append(
                DocumentTypeCandidate(
                    slug=rule.document_type_slug,
                    confidence=rule.confidence,
                    is_primary=True,
                    classification_method="deterministic_rule",
                    classifier_version=RULE_CLASSIFIER_VERSION,
                    evidence={
                        "rule_id": rule.rule_id,
                        "matched_term": matched,
                        "matched_fields": list(rule.fields),
                    },
                )
            )

        return DeterministicClassificationResult(
            topics=tuple(topics),
            document_types=tuple(document_types),
        )

    def _classify_metadata_topics(
        self,
        document_metadata: dict[str, Any],
    ) -> list[TopicCandidate]:
        raw_tags = document_metadata.get("tags")
        if not isinstance(raw_tags, list):
            return []

        normalized_values: set[str] = set()

        for raw_tag in raw_tags:
            if isinstance(raw_tag, str):
                value = normalize_match_text(raw_tag)
                if value:
                    normalized_values.add(value)
                continue

            if not isinstance(raw_tag, dict):
                continue

            for key in ("term", "label"):
                value = normalize_match_text(raw_tag.get(key))
                if value:
                    normalized_values.add(value)

        if not normalized_values:
            return []

        candidates: list[TopicCandidate] = []

        for mapping in self.metadata_topic_mappings:
            matched_term = next(
                (
                    term
                    for term in mapping.terms
                    if normalize_match_text(term)
                    in normalized_values
                ),
                None,
            )
            if matched_term is None:
                continue

            candidates.append(
                TopicCandidate(
                    slug=mapping.topic_slug,
                    confidence=mapping.confidence,
                    relationship_role="secondary",
                    classification_method="metadata_mapping",
                    classifier_version=RULE_CLASSIFIER_VERSION,
                    evidence={
                        "metadata_field": "tags",
                        "matched_term": matched_term,
                    },
                )
            )

        return candidates


def _contains_term(
    haystack: str,
    term: str,
) -> bool:
    normalized_term = normalize_match_text(term)

    if not haystack or not normalized_term:
        return False

    escaped = re.escape(normalized_term)
    prefix = r"(?<!\w)" if normalized_term[0].isalnum() else ""
    suffix = r"(?!\w)" if normalized_term[-1].isalnum() else ""

    return re.search(
        f"{prefix}{escaped}{suffix}",
        haystack,
        flags=re.UNICODE,
    ) is not None


def _first_matching_term(
    normalized_fields: dict[str, str],
    requested_fields: tuple[str, ...],
    terms: tuple[str, ...],
) -> str | None:
    for field_name in requested_fields:
        field_value = normalized_fields.get(field_name, "")

        for term in terms:
            if _contains_term(field_value, term):
                return term

    return None


def _require_string(
    payload: dict[str, Any],
    key: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Ruleset field {key!r} must be a nonempty string."
        )
    return value.strip()


def _require_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Rule confidence must be numeric."
        ) from exc

    if not 0.0 <= confidence <= 1.0:
        raise ValueError(
            "Rule confidence must be between 0 and 1."
        )

    return confidence


def _require_string_tuple(
    value: object,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(
            f"Ruleset field {field_name!r} must be a list."
        )

    items = tuple(
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    )

    if not items:
        raise ValueError(
            f"Ruleset field {field_name!r} cannot be empty."
        )

    return items


def _load_ruleset_uncached(
    path: Path,
) -> DeterministicRuleSet:
    raw = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError(
            "Deterministic ruleset root must be a JSON object."
        )

    metadata_mappings: list[MetadataTopicMapping] = []
    for item in raw.get("metadata_topic_mappings", []):
        if not isinstance(item, dict):
            raise ValueError(
                "metadata_topic_mappings entries must be objects."
            )

        metadata_mappings.append(
            MetadataTopicMapping(
                terms=_require_string_tuple(
                    item.get("terms"),
                    field_name="terms",
                ),
                topic_slug=_require_string(
                    item,
                    "topic_slug",
                ),
                confidence=_require_confidence(
                    item.get("confidence")
                ),
            )
        )

    topic_rules: list[TopicKeywordRule] = []
    for item in raw.get("topic_keyword_rules", []):
        if not isinstance(item, dict):
            raise ValueError(
                "topic_keyword_rules entries must be objects."
            )

        topic_rules.append(
            TopicKeywordRule(
                rule_id=_require_string(item, "id"),
                topic_slug=_require_string(
                    item,
                    "topic_slug",
                ),
                confidence=_require_confidence(
                    item.get("confidence")
                ),
                relationship_role=_require_string(
                    item,
                    "relationship_role",
                ),
                fields=_require_string_tuple(
                    item.get("fields"),
                    field_name="fields",
                ),
                any_terms=_require_string_tuple(
                    item.get("any_terms"),
                    field_name="any_terms",
                ),
            )
        )

    document_type_rules: list[DocumentTypeKeywordRule] = []
    for item in raw.get("document_type_keyword_rules", []):
        if not isinstance(item, dict):
            raise ValueError(
                "document_type_keyword_rules entries must be objects."
            )

        document_type_rules.append(
            DocumentTypeKeywordRule(
                rule_id=_require_string(item, "id"),
                document_type_slug=_require_string(
                    item,
                    "document_type_slug",
                ),
                confidence=_require_confidence(
                    item.get("confidence")
                ),
                fields=_require_string_tuple(
                    item.get("fields"),
                    field_name="fields",
                ),
                any_terms=_require_string_tuple(
                    item.get("any_terms"),
                    field_name="any_terms",
                ),
            )
        )

    return DeterministicRuleSet(
        ruleset_version=_require_string(
            raw,
            "ruleset_version",
        ),
        taxonomy_version=_require_string(
            raw,
            "taxonomy_version",
        ),
        metadata_topic_mappings=tuple(metadata_mappings),
        topic_keyword_rules=tuple(topic_rules),
        document_type_keyword_rules=tuple(
            document_type_rules
        ),
    )


@lru_cache(maxsize=8)
def _load_ruleset_cached(
    path_string: str,
    modified_ns: int,
) -> DeterministicRuleSet:
    del modified_ns
    return _load_ruleset_uncached(Path(path_string))


def load_deterministic_ruleset(
    path: Path | str = DEFAULT_RULESET_PATH,
) -> DeterministicRuleSet:
    resolved = Path(path).resolve()
    stat = resolved.stat()
    return _load_ruleset_cached(
        str(resolved),
        stat.st_mtime_ns,
    )


def clear_ruleset_cache() -> None:
    _load_ruleset_cached.cache_clear()
