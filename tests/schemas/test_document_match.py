from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.document_match import DocumentMatchCriteria


def test_document_match_criteria_normalizes_and_freezes_values() -> None:
    criteria = DocumentMatchCriteria(
        entity_ids=(4, 4, 7),
        entity_roles=(" subject ", "subject"),
        language_tags=("EN-us", "en-US"),
        minimum_confidence=Decimal("0.70"),
        effective_from=datetime(2026, 7, 27, tzinfo=UTC),
        text_query="  literal phrase  ",
    )

    assert criteria.entity_ids == (4, 7)
    assert criteria.entity_roles == ("subject",)
    assert criteria.language_tags == ("en-US",)
    assert criteria.text_query == "literal phrase"

    with pytest.raises(ValidationError):
        criteria.text_query = "changed"


@pytest.mark.parametrize(
    "values",
    [
        {"coverage_profile_id": 0},
        {"entity_ids": (-1,)},
        {"source_ids": (0,)},
        {"geographies": {"ids": [0]}},
        {"minimum_confidence": -0.01},
        {"minimum_confidence": 1.01},
        {"effective_from": datetime(2026, 7, 27)},  # noqa: DTZ001
    ],
)
def test_document_match_criteria_rejects_invalid_values(values) -> None:
    with pytest.raises(ValidationError):
        DocumentMatchCriteria(**values)
