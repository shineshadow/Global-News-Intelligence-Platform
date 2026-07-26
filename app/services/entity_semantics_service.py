from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EntityGeography, EntityTypeAssignment
from app.repositories import entity_semantics_repository
from app.services.exceptions import InvalidUpdateError, ResourceNotFoundError

EVIDENCE_COLLECTION_KEY = "supporting_evidence"
PROVENANCE_COLLECTION_KEY = "provenance_records"


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _validate_confidence(
    confidence: Decimal | float | None,
) -> Decimal | None:
    if confidence is None:
        return None

    normalized = Decimal(str(confidence))
    if normalized < 0 or normalized > 1:
        raise InvalidUpdateError("Confidence must be between 0 and 1.")
    return normalized


def _validate_interval(
    valid_from: datetime | None,
    valid_to: datetime | None,
) -> None:
    if valid_from is not None and valid_to is not None and valid_to < valid_from:
        raise InvalidUpdateError("valid_to must be greater than or equal to valid_from.")


def _new_support_collection(
    record: dict[str, Any] | None,
    *,
    collection_key: str,
) -> dict[str, Any]:
    if not record:
        return {}
    if not isinstance(record, dict):
        raise InvalidUpdateError(f"{collection_key} input must be a JSON object.")
    return {collection_key: [record]}


def _accumulate_support(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
    *,
    collection_key: str,
) -> tuple[dict[str, Any], bool]:
    """Append one distinct support record without losing legacy JSON."""

    if not incoming:
        return existing or {}, False
    if not isinstance(incoming, dict):
        raise InvalidUpdateError(f"{collection_key} input must be a JSON object.")

    current = existing or {}
    if not isinstance(current, dict):
        raise InvalidUpdateError(f"Stored {collection_key} must be a JSON object.")

    if collection_key not in current:
        records = [current] if current else []
    else:
        raw_records = current[collection_key]
        if not isinstance(raw_records, list) or not all(
            isinstance(item, dict) for item in raw_records
        ):
            raise InvalidUpdateError(f"Stored {collection_key} is not a list of JSON objects.")
        records = list(raw_records)
        legacy_fields = {key: value for key, value in current.items() if key != collection_key}
        if legacy_fields and legacy_fields not in records:
            records.insert(0, legacy_fields)

    if incoming in records:
        normalized = {collection_key: records}
        return normalized, normalized != current

    records.append(incoming)
    return {collection_key: records}, True


async def assign_entity_type(
    session: AsyncSession,
    *,
    entity_id: int,
    entity_type_slug: str,
    assignment_method: str,
    is_primary: bool = False,
    confidence: Decimal | float | None = None,
    evidence: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> EntityTypeAssignment:
    """Create or idempotently reuse an active canonical type assertion."""

    normalized_confidence = _validate_confidence(confidence)
    _validate_interval(valid_from, valid_to)

    entity = await entity_semantics_repository.get_entity(
        session,
        entity_id,
    )
    if entity is None:
        raise ResourceNotFoundError(f"Entity {entity_id} was not found.")

    entity_type = await entity_semantics_repository.get_entity_type_by_slug(
        session,
        entity_type_slug,
    )
    if entity_type is None or not entity_type.is_active:
        raise ResourceNotFoundError(f"Active entity type {entity_type_slug!r} was not found.")

    method = await entity_semantics_repository.get_assignment_method(
        session,
        assignment_method,
    )
    if method is None or not method.is_active:
        raise ResourceNotFoundError(
            f"Active assignment method {assignment_method!r} was not found."
        )

    existing = await entity_semantics_repository.get_active_entity_type_assignment(
        session,
        entity_id=entity_id,
        entity_type_id=entity_type.id,
    )

    if is_primary:
        await entity_semantics_repository.deactivate_other_primary_assignments(
            session,
            entity_id=entity_id,
            keep_assignment_id=existing.id if existing else None,
            superseded_at=_utcnow(),
        )

    if existing is not None:
        merged_evidence, evidence_changed = _accumulate_support(
            existing.evidence,
            evidence,
            collection_key=EVIDENCE_COLLECTION_KEY,
        )
        merged_provenance, provenance_changed = _accumulate_support(
            existing.provenance,
            provenance,
            collection_key=PROVENANCE_COLLECTION_KEY,
        )
        if evidence_changed:
            existing.evidence = merged_evidence
        if provenance_changed:
            existing.provenance = merged_provenance
        if is_primary and not existing.is_primary:
            existing.is_primary = True
            existing.updated_at = _utcnow()
        if evidence_changed or provenance_changed:
            existing.updated_at = _utcnow()
        if is_primary or evidence_changed or provenance_changed:
            await session.flush()
        return existing

    return await entity_semantics_repository.create_entity_type_assignment(
        session,
        {
            "entity_id": entity_id,
            "entity_type_id": entity_type.id,
            "assignment_method": assignment_method,
            "is_primary": is_primary,
            "confidence": normalized_confidence,
            "evidence": _new_support_collection(
                evidence,
                collection_key=EVIDENCE_COLLECTION_KEY,
            ),
            "provenance": _new_support_collection(
                provenance,
                collection_key=PROVENANCE_COLLECTION_KEY,
            ),
            "valid_from": valid_from,
            "valid_to": valid_to,
        },
    )


async def assert_entity_geography(
    session: AsyncSession,
    *,
    entity_id: int,
    geography_id: int,
    relationship_type: str,
    assignment_method: str,
    confidence: Decimal | float | None = None,
    evidence: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> EntityGeography:
    """Create or idempotently reuse an active entity-geography fact."""

    normalized_confidence = _validate_confidence(confidence)
    _validate_interval(valid_from, valid_to)

    entity = await entity_semantics_repository.get_entity(
        session,
        entity_id,
    )
    if entity is None:
        raise ResourceNotFoundError(f"Entity {entity_id} was not found.")

    geography = await entity_semantics_repository.get_geography(
        session,
        geography_id,
    )
    if geography is None or not geography.is_active:
        raise ResourceNotFoundError(f"Active geography {geography_id} was not found.")

    relationship = await entity_semantics_repository.get_relationship_type(
        session,
        relationship_type,
    )
    if relationship is None or not relationship.is_active:
        raise ResourceNotFoundError(
            f"Active entity-geography relationship type {relationship_type!r} was not found."
        )

    method = await entity_semantics_repository.get_assignment_method(
        session,
        assignment_method,
    )
    if method is None or not method.is_active:
        raise ResourceNotFoundError(
            f"Active assignment method {assignment_method!r} was not found."
        )

    existing = await entity_semantics_repository.get_active_entity_geography(
        session,
        entity_id=entity_id,
        geography_id=geography_id,
        relationship_type=relationship_type,
    )
    if existing is not None:
        merged_evidence, evidence_changed = _accumulate_support(
            existing.evidence,
            evidence,
            collection_key=EVIDENCE_COLLECTION_KEY,
        )
        merged_provenance, provenance_changed = _accumulate_support(
            existing.provenance,
            provenance,
            collection_key=PROVENANCE_COLLECTION_KEY,
        )
        if evidence_changed:
            existing.evidence = merged_evidence
        if provenance_changed:
            existing.provenance = merged_provenance
        if evidence_changed or provenance_changed:
            existing.updated_at = _utcnow()
            await session.flush()
        return existing

    return await entity_semantics_repository.create_entity_geography(
        session,
        {
            "entity_id": entity_id,
            "geography_id": geography_id,
            "relationship_type": relationship_type,
            "assignment_method": assignment_method,
            "confidence": normalized_confidence,
            "evidence": _new_support_collection(
                evidence,
                collection_key=EVIDENCE_COLLECTION_KEY,
            ),
            "provenance": _new_support_collection(
                provenance,
                collection_key=PROVENANCE_COLLECTION_KEY,
            ),
            "valid_from": valid_from,
            "valid_to": valid_to,
        },
    )


async def supersede_entity_geography(
    session: AsyncSession,
    assertion_id: int,
    *,
    superseded_at: datetime | None = None,
) -> EntityGeography:
    assertion = await session.get(EntityGeography, assertion_id)
    if assertion is None:
        raise ResourceNotFoundError(f"Entity-geography assertion {assertion_id} was not found.")
    if not assertion.is_active:
        return assertion

    await entity_semantics_repository.supersede_entity_geography(
        session,
        assertion,
        superseded_at=superseded_at or _utcnow(),
    )
    return assertion
