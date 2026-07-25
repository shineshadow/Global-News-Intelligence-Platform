import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.classification.normalization import normalize_match_text
from app.classification.rules import (
    DEFAULT_RULESET_PATH,
    RULE_CLASSIFIER_VERSION,
    DeterministicRuleSet,
    load_deterministic_ruleset,
)
from app.classification.types import (
    DeterministicClassificationResult,
    DocumentTypeCandidate,
    EntityCandidate,
    GeographyCandidate,
    TopicCandidate,
)
from app.database import async_session_factory
from app.repositories import classification_repository
from app.services.exceptions import ResourceNotFoundError


logger = logging.getLogger(__name__)

PIPELINE_VERSION = "deterministic-v1"
DEFAULTS_CLASSIFIER_VERSION = "classification-defaults-v1"
ENTITY_CLASSIFIER_VERSION = "entity-alias-v1"

_METHOD_PRIORITY = {
    "endpoint_default": 40,
    "source_default": 30,
    "metadata_mapping": 20,
    "deterministic_rule": 10,
}

_TOPIC_ROLE_PRIORITY = {
    "primary": 40,
    "secondary": 30,
    "contextual": 20,
    "mentioned": 10,
}


class ClassificationConfigurationError(ValueError):
    """Raised when deterministic classification configuration is invalid."""


@dataclass(slots=True, frozen=True)
class DeterministicClassificationSummary:
    document_id: int
    run_id: int | None
    status: str
    topics: int = 0
    geographies: int = 0
    entities: int = 0
    document_types: int = 0
    skipped_reason: str | None = None
    error: str | None = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _json_hash(payload: object) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _confidence(
    value: object,
    *,
    default: float,
) -> float:
    if value is None:
        return default

    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ClassificationConfigurationError(
            "Classification default confidence must be numeric."
        ) from exc

    if not 0.0 <= parsed <= 1.0:
        raise ClassificationConfigurationError(
            "Classification default confidence must be between 0 and 1."
        )

    return parsed


def _classification_defaults(
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    if not metadata:
        return {}

    value = metadata.get("classification_defaults")
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ClassificationConfigurationError(
            "classification_defaults must be a JSON object."
        )

    return value


def _list_of_objects(
    defaults: dict[str, Any],
    key: str,
) -> list[dict[str, Any]]:
    value = defaults.get(key, [])
    if value is None:
        return []

    if not isinstance(value, list):
        raise ClassificationConfigurationError(
            f"classification_defaults.{key} must be a list."
        )

    rows: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ClassificationConfigurationError(
                f"classification_defaults.{key} entries must be objects."
            )
        rows.append(item)

    return rows


def _required_slug(
    item: dict[str, Any],
    *,
    dimension: str,
) -> str:
    slug = item.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise ClassificationConfigurationError(
            f"{dimension} default requires a nonempty slug."
        )
    return slug.strip()


def _default_candidates(
    metadata: dict[str, Any] | None,
    *,
    method: str,
) -> DeterministicClassificationResult:
    defaults = _classification_defaults(metadata)

    if not defaults:
        return DeterministicClassificationResult()

    confidence_defaults = {
        "source_default": {
            "topic": 0.90,
            "geography": 0.90,
            "document_type": 0.95,
        },
        "endpoint_default": {
            "topic": 0.95,
            "geography": 0.95,
            "document_type": 0.98,
        },
    }[method]

    topics = tuple(
        TopicCandidate(
            slug=_required_slug(
                item,
                dimension="Topic",
            ),
            confidence=_confidence(
                item.get("confidence"),
                default=confidence_defaults["topic"],
            ),
            relationship_role=str(
                item.get("role") or "primary"
            ),
            classification_method=method,  # type: ignore[arg-type]
            classifier_version=DEFAULTS_CLASSIFIER_VERSION,
            evidence={
                "default_scope": method,
                "configured_default": item,
            },
        )
        for item in _list_of_objects(defaults, "topics")
    )

    geographies = tuple(
        GeographyCandidate(
            slug=_required_slug(
                item,
                dimension="Geography",
            ),
            confidence=_confidence(
                item.get("confidence"),
                default=confidence_defaults["geography"],
            ),
            relationship_role=str(
                item.get("role") or "primary_subject"
            ),
            classification_method=method,  # type: ignore[arg-type]
            classifier_version=DEFAULTS_CLASSIFIER_VERSION,
            evidence={
                "default_scope": method,
                "configured_default": item,
            },
        )
        for item in _list_of_objects(
            defaults,
            "geographies",
        )
    )

    document_types = tuple(
        DocumentTypeCandidate(
            slug=_required_slug(
                item,
                dimension="Document type",
            ),
            confidence=_confidence(
                item.get("confidence"),
                default=confidence_defaults["document_type"],
            ),
            is_primary=bool(
                item.get("primary", True)
            ),
            classification_method=method,  # type: ignore[arg-type]
            classifier_version=DEFAULTS_CLASSIFIER_VERSION,
            evidence={
                "default_scope": method,
                "configured_default": item,
            },
        )
        for item in _list_of_objects(
            defaults,
            "document_types",
        )
    )

    return DeterministicClassificationResult(
        topics=topics,
        geographies=geographies,
        document_types=document_types,
    )


def _best_topic_candidates(
    candidates: list[TopicCandidate],
) -> list[TopicCandidate]:
    best: dict[str, TopicCandidate] = {}

    for candidate in candidates:
        current = best.get(candidate.slug)
        if current is None:
            best[candidate.slug] = candidate
            continue

        current_score = (
            _METHOD_PRIORITY.get(
                current.classification_method,
                0,
            ),
            current.confidence,
            _TOPIC_ROLE_PRIORITY.get(
                current.relationship_role,
                0,
            ),
        )
        candidate_score = (
            _METHOD_PRIORITY.get(
                candidate.classification_method,
                0,
            ),
            candidate.confidence,
            _TOPIC_ROLE_PRIORITY.get(
                candidate.relationship_role,
                0,
            ),
        )

        if candidate_score > current_score:
            best[candidate.slug] = candidate

    return sorted(
        best.values(),
        key=lambda item: item.slug,
    )


def _best_geography_candidates(
    candidates: list[GeographyCandidate],
) -> list[GeographyCandidate]:
    best: dict[tuple[str, str], GeographyCandidate] = {}

    for candidate in candidates:
        key = (
            candidate.slug,
            candidate.relationship_role,
        )
        current = best.get(key)

        if current is None:
            best[key] = candidate
            continue

        current_score = (
            _METHOD_PRIORITY.get(
                current.classification_method,
                0,
            ),
            current.confidence,
        )
        candidate_score = (
            _METHOD_PRIORITY.get(
                candidate.classification_method,
                0,
            ),
            candidate.confidence,
        )

        if candidate_score > current_score:
            best[key] = candidate

    return sorted(
        best.values(),
        key=lambda item: (
            item.slug,
            item.relationship_role,
        ),
    )


def _best_document_type_candidates(
    candidates: list[DocumentTypeCandidate],
) -> list[DocumentTypeCandidate]:
    best: dict[str, DocumentTypeCandidate] = {}

    for candidate in candidates:
        current = best.get(candidate.slug)

        if current is None:
            best[candidate.slug] = candidate
            continue

        current_score = (
            _METHOD_PRIORITY.get(
                current.classification_method,
                0,
            ),
            current.confidence,
        )
        candidate_score = (
            _METHOD_PRIORITY.get(
                candidate.classification_method,
                0,
            ),
            candidate.confidence,
        )

        if candidate_score > current_score:
            best[candidate.slug] = candidate

    values = list(best.values())
    primary_candidates = [
        item
        for item in values
        if item.is_primary
    ]

    if primary_candidates:
        winner = max(
            primary_candidates,
            key=lambda item: (
                _METHOD_PRIORITY.get(
                    item.classification_method,
                    0,
                ),
                item.confidence,
            ),
        )
        values = [
            (
                item
                if item.slug == winner.slug
                else replace(
                    item,
                    is_primary=False,
                )
            )
            for item in values
        ]

    return sorted(values, key=lambda item: item.slug)


def _best_entity_candidates(
    candidates: list[EntityCandidate],
) -> list[EntityCandidate]:
    best: dict[tuple[int, str], EntityCandidate] = {}

    for candidate in candidates:
        key = (
            candidate.entity_id,
            candidate.entity_role,
        )
        current = best.get(key)

        if (
            current is None
            or candidate.confidence > current.confidence
        ):
            best[key] = candidate

    return sorted(
        best.values(),
        key=lambda item: (
            item.entity_id,
            item.entity_role,
        ),
    )


def _entity_alias_is_matchable(
    normalized_alias: str,
    alias_type: str | None,
) -> bool:
    if not normalized_alias:
        return False

    if (
        normalized_alias.isascii()
        and len(normalized_alias) < 3
        and alias_type != "short_exact"
    ):
        return False

    return True


def _contains_alias(
    normalized_text: str,
    normalized_alias: str,
) -> bool:
    escaped = re.escape(normalized_alias)
    prefix = (
        r"(?<!\w)"
        if normalized_alias[0].isalnum()
        else ""
    )
    suffix = (
        r"(?!\w)"
        if normalized_alias[-1].isalnum()
        else ""
    )

    return re.search(
        f"{prefix}{escaped}{suffix}",
        normalized_text,
        flags=re.UNICODE,
    ) is not None


def _entity_candidates_from_aliases(
    *,
    title: str,
    summary: str | None,
    content: str | None,
    aliases: list[tuple[Any, Any]],
) -> list[EntityCandidate]:
    normalized_text = " ".join(
        value
        for value in (
            normalize_match_text(title),
            normalize_match_text(summary),
            normalize_match_text(content),
        )
        if value
    )

    if not normalized_text:
        return []

    candidates: list[EntityCandidate] = []

    for alias, entity in aliases:
        normalized_alias = normalize_match_text(
            alias.normalized_alias or alias.alias
        )

        if not _entity_alias_is_matchable(
            normalized_alias,
            alias.alias_type,
        ):
            continue

        if not _contains_alias(
            normalized_text,
            normalized_alias,
        ):
            continue

        candidates.append(
            EntityCandidate(
                entity_id=entity.id,
                confidence=0.90,
                entity_role="mentioned",
                classification_method="deterministic_rule",
                classifier_version=ENTITY_CLASSIFIER_VERSION,
                mention_text=alias.alias,
                evidence={
                    "matcher": "entity_alias",
                    "alias_id": alias.id,
                    "alias": alias.alias,
                    "language": alias.language,
                },
            )
        )

    return _best_entity_candidates(candidates)


async def _publisher_context_geography(
    session: AsyncSession,
    *,
    source_country: str,
    ruleset: DeterministicRuleSet,
) -> GeographyCandidate | None:
    normalized_country = normalize_match_text(
        source_country
    )

    if not normalized_country:
        return None

    geographies = (
        await classification_repository
        .get_active_geographies(session)
    )

    for geography in geographies:
        if geography.geography_type not in {
            "country",
            "country_or_area",
            "territory",
            "de_facto_state",
        }:
            continue

        if (
            normalize_match_text(geography.name)
            != normalized_country
        ):
            continue

        return GeographyCandidate(
            slug=geography.slug,
            confidence=0.60,
            relationship_role="publisher_context",
            classification_method="source_default",
            classifier_version=DEFAULTS_CLASSIFIER_VERSION,
            taxonomy_version=ruleset.taxonomy_version,
            evidence={
                "source_country": source_country,
                "derivation": "source.country",
            },
        )

    return None


def _classification_input_hash(
    *,
    document: Any,
    source: Any,
    endpoint: Any | None,
    entity_state: dict[str, Any],
    ruleset_fingerprint: str,
) -> str:
    return _json_hash(
        {
            "document": {
                "content_hash": document.content_hash,
                "language": document.language,
                "canonical_url": document.canonical_url,
                "metadata": document.document_metadata or {},
            },
            "source": {
                "id": source.id,
                "country": source.country,
                "classification_defaults": (
                    (source.source_metadata or {}).get(
                        "classification_defaults"
                    )
                ),
            },
            "endpoint": (
                {
                    "id": endpoint.id,
                    "url": endpoint.url,
                    "classification_defaults": (
                        (
                            endpoint.endpoint_metadata
                            or {}
                        ).get(
                            "classification_defaults"
                        )
                    ),
                }
                if endpoint is not None
                else None
            ),
            "entity_resolution_state": entity_state,
            "ruleset_fingerprint": ruleset_fingerprint,
        }
    )


def _output_hash(
    *,
    topic_rows: list[dict[str, Any]],
    geography_rows: list[dict[str, Any]],
    entity_rows: list[dict[str, Any]],
    document_type_rows: list[dict[str, Any]],
) -> str:
    def clean(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        for row in rows:
            cleaned.append(
                {
                    key: value
                    for key, value in row.items()
                    if key not in {
                        "classification_run_id",
                        "document_id",
                    }
                }
            )
        return sorted(
            cleaned,
            key=lambda item: json.dumps(
                item,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            ),
        )

    return _json_hash(
        {
            "topics": clean(topic_rows),
            "geographies": clean(geography_rows),
            "entities": clean(entity_rows),
            "document_types": clean(
                document_type_rows
            ),
        }
    )


async def _build_candidates(
    session: AsyncSession,
    *,
    document: Any,
    source: Any,
    endpoint: Any | None,
    ruleset: DeterministicRuleSet,
) -> DeterministicClassificationResult:
    source_defaults = _default_candidates(
        source.source_metadata or {},
        method="source_default",
    )
    endpoint_defaults = (
        _default_candidates(
            endpoint.endpoint_metadata or {},
            method="endpoint_default",
        )
        if endpoint is not None
        else DeterministicClassificationResult()
    )
    rule_result = ruleset.classify(
        title=document.title_original,
        summary=document.summary_original,
        content=document.content_original,
        canonical_url=document.canonical_url,
        document_metadata=(
            document.document_metadata or {}
        ),
    )

    publisher_context = (
        await _publisher_context_geography(
            session,
            source_country=source.country,
            ruleset=ruleset,
        )
    )

    aliases = (
        await classification_repository
        .get_active_entity_aliases(session)
    )
    entity_candidates = (
        _entity_candidates_from_aliases(
            title=document.title_original,
            summary=document.summary_original,
            content=document.content_original,
            aliases=aliases,
        )
    )

    topics = _best_topic_candidates(
        [
            *source_defaults.topics,
            *endpoint_defaults.topics,
            *rule_result.topics,
        ]
    )

    geographies = _best_geography_candidates(
        [
            *source_defaults.geographies,
            *endpoint_defaults.geographies,
            *(
                [publisher_context]
                if publisher_context is not None
                else []
            ),
        ]
    )

    document_types = (
        _best_document_type_candidates(
            [
                *source_defaults.document_types,
                *endpoint_defaults.document_types,
                *rule_result.document_types,
            ]
        )
    )

    return DeterministicClassificationResult(
        topics=tuple(topics),
        geographies=tuple(geographies),
        entities=tuple(entity_candidates),
        document_types=tuple(document_types),
    )


async def _persist_candidates(
    session: AsyncSession,
    *,
    document_id: int,
    run_id: int,
    ruleset: DeterministicRuleSet,
    candidates: DeterministicClassificationResult,
    now: datetime,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    topic_map = (
        await classification_repository
        .get_topics_by_slugs(
            session,
            {
                candidate.slug
                for candidate in candidates.topics
            },
        )
    )
    geography_map = (
        await classification_repository
        .get_geographies_by_slugs(
            session,
            {
                candidate.slug
                for candidate
                in candidates.geographies
            },
        )
    )
    document_type_map = (
        await classification_repository
        .get_document_types_by_slugs(
            session,
            {
                candidate.slug
                for candidate
                in candidates.document_types
            },
        )
    )

    missing_topics = {
        item.slug
        for item in candidates.topics
    } - set(topic_map)
    missing_geographies = {
        item.slug
        for item in candidates.geographies
    } - set(geography_map)
    missing_document_types = {
        item.slug
        for item in candidates.document_types
    } - set(document_type_map)

    missing = {
        "topics": sorted(missing_topics),
        "geographies": sorted(
            missing_geographies
        ),
        "document_types": sorted(
            missing_document_types
        ),
    }
    missing = {
        key: value
        for key, value in missing.items()
        if value
    }

    if missing:
        raise ClassificationConfigurationError(
            "Classification configuration references "
            f"unknown/inactive canonical slugs: {missing}"
        )

    await (
        classification_repository
        .deactivate_current_deterministic_assertions(
            session,
            document_id=document_id,
            superseded_at=now,
        )
    )

    manual_topic_keys = (
        await classification_repository
        .get_active_manual_topic_keys(
            session,
            document_id,
        )
    )
    manual_geography_keys = (
        await classification_repository
        .get_active_manual_geography_keys(
            session,
            document_id,
        )
    )
    manual_entity_keys = (
        await classification_repository
        .get_active_manual_entity_keys(
            session,
            document_id,
        )
    )
    manual_document_types = (
        await classification_repository
        .get_active_manual_document_type_rows(
            session,
            document_id,
        )
    )

    manual_document_type_ids = {
        row[0]
        for row in manual_document_types
    }
    has_manual_primary = any(
        row[1]
        for row in manual_document_types
    )

    topic_rows: list[dict[str, Any]] = []
    for candidate in candidates.topics:
        topic = topic_map[candidate.slug]
        key = (
            topic.id,
            candidate.relationship_role,
        )
        if key in manual_topic_keys:
            continue

        topic_rows.append(
            {
                "document_id": document_id,
                "topic_id": topic.id,
                "confidence": Decimal(
                    str(candidate.confidence)
                ),
                "relationship_role": (
                    candidate.relationship_role
                ),
                "classification_method": (
                    candidate.classification_method
                ),
                "classifier_version": (
                    candidate.classifier_version
                ),
                "taxonomy_version": (
                    ruleset.taxonomy_version
                ),
                "classification_run_id": run_id,
                "is_manual_override": False,
                "evidence": candidate.evidence,
                "is_active": True,
            }
        )

    geography_rows: list[dict[str, Any]] = []
    for candidate in candidates.geographies:
        geography = geography_map[candidate.slug]
        key = (
            geography.id,
            candidate.relationship_role,
        )
        if key in manual_geography_keys:
            continue

        geography_rows.append(
            {
                "document_id": document_id,
                "geography_id": geography.id,
                "confidence": Decimal(
                    str(candidate.confidence)
                ),
                "relationship_role": (
                    candidate.relationship_role
                ),
                "classification_method": (
                    candidate.classification_method
                ),
                "classifier_version": (
                    candidate.classifier_version
                ),
                "taxonomy_version": (
                    candidate.taxonomy_version
                ),
                "classification_run_id": run_id,
                "is_manual_override": False,
                "evidence": candidate.evidence,
                "is_active": True,
            }
        )

    entity_rows: list[dict[str, Any]] = []
    for candidate in candidates.entities:
        key = (
            candidate.entity_id,
            candidate.entity_role,
        )
        if key in manual_entity_keys:
            continue

        entity_rows.append(
            {
                "document_id": document_id,
                "entity_id": candidate.entity_id,
                "mention_text": candidate.mention_text,
                "entity_role": candidate.entity_role,
                "confidence": Decimal(
                    str(candidate.confidence)
                ),
                "classification_method": (
                    candidate.classification_method
                ),
                "classifier_version": (
                    candidate.classifier_version
                ),
                "classification_run_id": run_id,
                "is_manual_override": False,
                "evidence": candidate.evidence,
                "is_active": True,
            }
        )

    document_type_rows: list[
        dict[str, Any]
    ] = []
    for candidate in candidates.document_types:
        document_type = document_type_map[
            candidate.slug
        ]

        if (
            document_type.id
            in manual_document_type_ids
        ):
            continue

        if (
            candidate.is_primary
            and has_manual_primary
        ):
            continue

        document_type_rows.append(
            {
                "document_id": document_id,
                "document_type_id": document_type.id,
                "is_primary": candidate.is_primary,
                "confidence": Decimal(
                    str(candidate.confidence)
                ),
                "classification_method": (
                    candidate.classification_method
                ),
                "classifier_version": (
                    candidate.classifier_version
                ),
                "classification_run_id": run_id,
                "is_manual_override": False,
                "evidence": candidate.evidence,
                "is_active": True,
            }
        )

    await classification_repository.create_document_topics(
        session,
        topic_rows,
    )
    await (
        classification_repository
        .create_document_geographies(
            session,
            geography_rows,
        )
    )
    await (
        classification_repository
        .create_document_entities(
            session,
            entity_rows,
        )
    )
    await (
        classification_repository
        .create_document_type_assignments(
            session,
            document_type_rows,
        )
    )

    return (
        topic_rows,
        geography_rows,
        entity_rows,
        document_type_rows,
    )


async def classify_document_deterministically(
    session: AsyncSession,
    document_id: int,
    *,
    trigger: str = "manual",
    force: bool = False,
    ruleset_path: Path | str = DEFAULT_RULESET_PATH,
) -> DeterministicClassificationSummary:
    context = (
        await classification_repository
        .get_document_context(
            session,
            document_id,
        )
    )

    if context is None:
        raise ResourceNotFoundError(
            f"Document {document_id} was not found."
        )

    document, source, endpoint = context
    ruleset = load_deterministic_ruleset(
        ruleset_path
    )
    entity_state = (
        await classification_repository
        .get_entity_resolution_state(session)
    )
    ruleset_fingerprint = _json_hash(
        asdict(ruleset)
    )
    input_hash = _classification_input_hash(
        document=document,
        source=source,
        endpoint=endpoint,
        entity_state=entity_state,
        ruleset_fingerprint=ruleset_fingerprint,
    )

    if not force:
        prior_run = (
            await classification_repository
            .get_matching_successful_run(
                session,
                document_id=document.id,
                pipeline_version=PIPELINE_VERSION,
                taxonomy_version=(
                    ruleset.taxonomy_version
                ),
                ruleset_version=(
                    ruleset.ruleset_version
                ),
                input_hash=input_hash,
            )
        )
        if prior_run is not None:
            return DeterministicClassificationSummary(
                document_id=document.id,
                run_id=prior_run.id,
                status="skipped",
                skipped_reason=(
                    "matching_successful_run"
                ),
            )

    started_at = _utcnow()

    run = (
        await classification_repository
        .create_classification_run(
            session,
            {
                "document_id": document.id,
                "pipeline_version": PIPELINE_VERSION,
                "taxonomy_version": (
                    ruleset.taxonomy_version
                ),
                "started_at": started_at,
                "status": "running",
                "language": document.language,
                "classifier_versions": {
                    "defaults": (
                        DEFAULTS_CLASSIFIER_VERSION
                    ),
                    "rules": (
                        RULE_CLASSIFIER_VERSION
                    ),
                    "entity_alias_matcher": (
                        ENTITY_CLASSIFIER_VERSION
                    ),
                },
                "ruleset_version": (
                    ruleset.ruleset_version
                ),
                "input_hash": input_hash,
                "run_metadata": {
                    "trigger": trigger,
                    "force": force,
                    "entity_resolution_state": (
                        entity_state
                    ),
                    "ruleset_fingerprint": (
                        ruleset_fingerprint
                    ),
                    "ruleset_path": str(
                        Path(ruleset_path)
                    ),
                },
            },
        )
    )

    try:
        async with session.begin_nested():
            candidates = await _build_candidates(
                session,
                document=document,
                source=source,
                endpoint=endpoint,
                ruleset=ruleset,
            )

            now = _utcnow()
            (
                topic_rows,
                geography_rows,
                entity_rows,
                document_type_rows,
            ) = await _persist_candidates(
                session,
                document_id=document.id,
                run_id=run.id,
                ruleset=ruleset,
                candidates=candidates,
                now=now,
            )

        completed_at = _utcnow()
        output_hash = _output_hash(
            topic_rows=topic_rows,
            geography_rows=geography_rows,
            entity_rows=entity_rows,
            document_type_rows=(
                document_type_rows
            ),
        )

        await (
            classification_repository
            .update_classification_run(
                session,
                run,
                {
                    "status": "succeeded",
                    "completed_at": completed_at,
                    "output_hash": output_hash,
                    "error": None,
                },
            )
        )

        return DeterministicClassificationSummary(
            document_id=document.id,
            run_id=run.id,
            status="succeeded",
            topics=len(topic_rows),
            geographies=len(geography_rows),
            entities=len(entity_rows),
            document_types=len(
                document_type_rows
            ),
        )

    except Exception as exc:
        logger.warning(
            "Deterministic classification failed "
            "for document %s: %s",
            document.id,
            exc,
            exc_info=True,
        )

        await (
            classification_repository
            .update_classification_run(
                session,
                run,
                {
                    "status": "failed",
                    "completed_at": _utcnow(),
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                },
            )
        )

        return DeterministicClassificationSummary(
            document_id=document.id,
            run_id=run.id,
            status="failed",
            error=str(exc),
        )


async def classify_document_by_id(
    document_id: int,
    *,
    trigger: str = "manual",
    force: bool = False,
    ruleset_path: Path | str = DEFAULT_RULESET_PATH,
) -> DeterministicClassificationSummary:
    async with async_session_factory() as session:
        async with session.begin():
            return (
                await classify_document_deterministically(
                    session,
                    document_id,
                    trigger=trigger,
                    force=force,
                    ruleset_path=ruleset_path,
                )
            )
