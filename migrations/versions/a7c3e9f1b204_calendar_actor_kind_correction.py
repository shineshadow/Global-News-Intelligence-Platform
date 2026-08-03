"""correct Calendar actor-kind vocabulary

Revision ID: a7c3e9f1b204
Revises: f29b6d8e3c10
Create Date: 2026-07-28

Replace the unapproved ai_job Calendar actor kind with the approved
internal_agent and external_model distinction. Refuse to guess when
historical ai_job provenance is ambiguous.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e9f1b204"
down_revision: str | Sequence[str] | None = "f29b6d8e3c10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CALENDAR_ACTOR_TABLES = (
    "intelligence_calendar_events",
    "intelligence_calendar_event_revisions",
    "intelligence_calendar_event_aliases",
    "intelligence_calendar_event_recurrence_rules",
    "intelligence_calendar_event_recurrence_exceptions",
    "intelligence_calendar_event_occurrences",
    "intelligence_calendar_occurrence_schedule_revisions",
    "intelligence_calendar_event_evidence",
    "intelligence_calendar_event_state_transitions",
    "intelligence_calendar_event_geographies",
    "intelligence_calendar_event_topics",
    "intelligence_calendar_event_entities",
    "intelligence_calendar_event_sources",
    "intelligence_calendar_event_documents",
    "intelligence_calendar_event_coverage_policies",
    "intelligence_calendar_occurrence_policy_overrides",
    "intelligence_calendar_policy_watch_sources",
    "intelligence_calendar_policy_search_terms",
    "intelligence_calendar_policy_document_types",
    "intelligence_calendar_policy_content_formats",
    "intelligence_calendar_event_monitors",
    "intelligence_calendar_event_merge_history",
)

OLD_ACTORS = "('operator', 'system', 'import', 'ai_job')"
NEW_ACTORS = (
    "('operator', 'system', 'import', 'internal_agent', 'external_model')"
)


def _count_actor(connection, actor_kind: str) -> list[tuple[str, int]]:
    counts: list[tuple[str, int]] = []
    for table_name in CALENDAR_ACTOR_TABLES:
        count = int(
            connection.execute(
                sa.text(
                    f"SELECT count(*) FROM {table_name} "
                    "WHERE actor_kind = :actor_kind"
                ),
                {"actor_kind": actor_kind},
            ).scalar_one()
        )
        if count:
            counts.append((table_name, count))
    return counts


def _replace_constraints(actor_values: str) -> None:
    for table_name in CALENDAR_ACTOR_TABLES:
        constraint_name = f"ck_{table_name}_actor_kind"
        op.drop_constraint(
            op.f(constraint_name),
            table_name,
            type_="check",
        )
        op.create_check_constraint(
            op.f(constraint_name),
            table_name,
            f"actor_kind IN {actor_values}",
        )


def upgrade() -> None:
    connection = op.get_bind()
    ambiguous = _count_actor(connection, "ai_job")
    if ambiguous:
        detail = ", ".join(
            f"{table_name}={count}"
            for table_name, count in ambiguous
        )
        raise RuntimeError(
            "Refusing Calendar actor-kind correction: ai_job rows require "
            f"explicit provenance-based classification ({detail})."
        )

    _replace_constraints(NEW_ACTORS)


def downgrade() -> None:
    connection = op.get_bind()
    incompatible = [
        *_count_actor(connection, "internal_agent"),
        *_count_actor(connection, "external_model"),
    ]
    if incompatible:
        detail = ", ".join(
            f"{table_name}={count}"
            for table_name, count in incompatible
        )
        raise RuntimeError(
            "Refusing Calendar actor-kind downgrade: internal_agent or "
            f"external_model provenance would be lost ({detail})."
        )

    _replace_constraints(OLD_ACTORS)
