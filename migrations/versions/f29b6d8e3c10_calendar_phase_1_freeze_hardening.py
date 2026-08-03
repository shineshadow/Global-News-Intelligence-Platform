"""harden Calendar Phase 1 freeze invariants

Revision ID: f29b6d8e3c10
Revises: e27a6c9d4f10
Create Date: 2026-07-27

Require uncertainty-safe precision, legal Phase 1 state transitions,
same-transaction state history, and forward-only current revision pointers.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f29b6d8e3c10"
down_revision: str | Sequence[str] | None = "e27a6c9d4f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEDULE_TABLE = "intelligence_calendar_occurrence_schedule_revisions"
TRANSITION_TABLE = "intelligence_calendar_event_state_transitions"
RULE_TABLE = "intelligence_calendar_event_recurrence_rules"


def upgrade() -> None:
    op.create_check_constraint(
        op.f(f"ck_{SCHEDULE_TABLE}_unknown_precision"),
        SCHEDULE_TABLE,
        "(temporal_mode = 'unknown' "
        "AND date_precision = 'unknown' "
        "AND time_precision = 'unknown') "
        "OR temporal_mode <> 'unknown'",
    )
    op.create_check_constraint(
        op.f(f"ck_{SCHEDULE_TABLE}_timed_time_precision"),
        SCHEDULE_TABLE,
        "(temporal_mode = 'timed' "
        "AND time_precision <> 'not_applicable') "
        "OR temporal_mode <> 'timed'",
    )
    op.create_check_constraint(
        op.f(f"ck_{RULE_TABLE}_all_day_duration"),
        RULE_TABLE,
        "NOT all_day OR duration_seconds IS NULL "
        "OR duration_seconds % 86400 = 0",
    )
    op.create_check_constraint(
        op.f(f"ck_{TRANSITION_TABLE}_phase1_no_outcome"),
        TRANSITION_TABLE,
        "dimension <> 'outcome'",
    )
    op.create_check_constraint(
        op.f(f"ck_{TRANSITION_TABLE}_legal_transition"),
        TRANSITION_TABLE,
        "(dimension = 'identity' AND ("
        "(previous_state = 'active' "
        "AND next_state IN ('archived', 'merged')) OR "
        "(previous_state = 'archived' AND next_state = 'active'))) OR "
        "(dimension = 'validation' AND ("
        "(previous_state = 'candidate' "
        "AND next_state IN ('probable', 'disputed', 'rejected')) OR "
        "(previous_state = 'probable' "
        "AND next_state IN ('verified', 'disputed', 'rejected')) OR "
        "(previous_state = 'verified' "
        "AND next_state IN ('confirmed', 'disputed', 'rejected')) OR "
        "(previous_state = 'confirmed' AND next_state = 'disputed') OR "
        "(previous_state = 'disputed' "
        "AND next_state IN "
        "('candidate', 'probable', 'verified', 'confirmed', 'rejected')) OR "
        "(previous_state = 'rejected' AND next_state = 'candidate'))) OR "
        "(dimension = 'schedule' AND ("
        "(previous_state = 'tentative' "
        "AND next_state IN ('scheduled', 'postponed', 'cancelled')) OR "
        "(previous_state = 'scheduled' "
        "AND next_state IN ('postponed', 'cancelled')) OR "
        "(previous_state = 'postponed' "
        "AND next_state IN ('scheduled', 'cancelled'))))",
    )

    op.execute(
        """
        CREATE FUNCTION calendar_require_state_history() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE inherited_validation text;
        BEGIN
            IF TG_TABLE_NAME = 'intelligence_calendar_events' THEN
                IF OLD.identity_state IS DISTINCT FROM NEW.identity_state
                   AND NOT EXISTS (
                       SELECT 1
                       FROM intelligence_calendar_event_state_transitions
                       WHERE event_id = NEW.id
                         AND occurrence_id IS NULL
                         AND dimension = 'identity'
                         AND previous_state = OLD.identity_state
                         AND next_state = NEW.identity_state
                         AND transitioned_at >= transaction_timestamp()
                   )
                THEN
                    RAISE EXCEPTION
                        'Event identity change requires same-transaction history';
                END IF;
                IF OLD.validation_state IS DISTINCT FROM NEW.validation_state
                   AND NOT EXISTS (
                       SELECT 1
                       FROM intelligence_calendar_event_state_transitions
                       WHERE event_id = NEW.id
                         AND occurrence_id IS NULL
                         AND dimension = 'validation'
                         AND previous_state = OLD.validation_state
                         AND next_state = NEW.validation_state
                         AND transitioned_at >= transaction_timestamp()
                   )
                THEN
                    RAISE EXCEPTION
                        'Event validation change requires same-transaction history';
                END IF;
                IF NEW.identity_state = 'merged'
                   AND (
                       NEW.merged_into_event_id IS NULL
                       OR NOT EXISTS (
                           SELECT 1
                           FROM intelligence_calendar_event_merge_history
                           WHERE loser_event_id = NEW.id
                             AND winner_event_id = NEW.merged_into_event_id
                             AND merged_at >= transaction_timestamp()
                       )
                   )
                THEN
                    RAISE EXCEPTION
                        'merged Event requires same-transaction merge history';
                END IF;
            ELSE
                IF OLD.schedule_state IS DISTINCT FROM NEW.schedule_state
                   AND NOT EXISTS (
                       SELECT 1
                       FROM intelligence_calendar_event_state_transitions
                       WHERE event_id = NEW.event_id
                         AND occurrence_id = NEW.id
                         AND dimension = 'schedule'
                         AND previous_state = OLD.schedule_state
                         AND next_state = NEW.schedule_state
                         AND transitioned_at >= transaction_timestamp()
                   )
                THEN
                    RAISE EXCEPTION
                        'Occurrence schedule change requires same-transaction history';
                END IF;
                IF OLD.validation_state IS DISTINCT FROM NEW.validation_state THEN
                    SELECT validation_state INTO inherited_validation
                    FROM intelligence_calendar_events
                    WHERE id = NEW.event_id;
                    IF NOT EXISTS (
                        SELECT 1
                        FROM intelligence_calendar_event_state_transitions
                        WHERE event_id = NEW.event_id
                          AND occurrence_id = NEW.id
                          AND dimension = 'validation'
                          AND previous_state = COALESCE(
                              OLD.validation_state,
                              inherited_validation
                          )
                          AND next_state = NEW.validation_state
                          AND transitioned_at >= transaction_timestamp()
                    )
                    THEN
                        RAISE EXCEPTION
                            'Occurrence validation change requires '
                            'same-transaction history';
                    END IF;
                END IF;
            END IF;
            RETURN NULL;
        END
        $$;

        CREATE FUNCTION calendar_require_forward_revision() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE old_number integer;
        DECLARE new_number integer;
        BEGIN
            IF TG_TABLE_NAME = 'intelligence_calendar_events' THEN
                IF OLD.current_revision_id = NEW.current_revision_id THEN
                    RETURN NEW;
                END IF;
                SELECT revision_number INTO old_number
                FROM intelligence_calendar_event_revisions
                WHERE id = OLD.current_revision_id AND event_id = OLD.id;
                SELECT revision_number INTO new_number
                FROM intelligence_calendar_event_revisions
                WHERE id = NEW.current_revision_id AND event_id = NEW.id;
            ELSE
                IF OLD.current_schedule_revision_id
                   = NEW.current_schedule_revision_id
                THEN
                    RETURN NEW;
                END IF;
                SELECT revision_number INTO old_number
                FROM intelligence_calendar_occurrence_schedule_revisions
                WHERE id = OLD.current_schedule_revision_id
                  AND occurrence_id = OLD.id;
                SELECT revision_number INTO new_number
                FROM intelligence_calendar_occurrence_schedule_revisions
                WHERE id = NEW.current_schedule_revision_id
                  AND occurrence_id = NEW.id;
            END IF;
            IF new_number IS NULL OR old_number IS NULL
               OR new_number <> old_number + 1
            THEN
                RAISE EXCEPTION
                    'Calendar current revision pointers advance exactly one revision';
            END IF;
            RETURN NEW;
        END
        $$;

        CREATE CONSTRAINT TRIGGER trg_calendar_events_state_history
        AFTER UPDATE ON intelligence_calendar_events
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION calendar_require_state_history();

        CREATE CONSTRAINT TRIGGER trg_calendar_occurrences_state_history
        AFTER UPDATE ON intelligence_calendar_event_occurrences
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION calendar_require_state_history();

        CREATE CONSTRAINT TRIGGER trg_calendar_events_forward_revision
        AFTER UPDATE ON intelligence_calendar_events
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION calendar_require_forward_revision();

        CREATE CONSTRAINT TRIGGER trg_calendar_occurrences_forward_revision
        AFTER UPDATE ON intelligence_calendar_event_occurrences
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION calendar_require_forward_revision();
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.execute(
        sa.text(
            "SELECT EXISTS ("
            "SELECT 1 FROM intelligence_calendar_events LIMIT 1)"
        )
    ).scalar_one():
        raise RuntimeError(
            "Refusing to remove Calendar freeze hardening: "
            "Calendar-owned state exists."
        )

    op.execute(
        """
        DROP TRIGGER trg_calendar_occurrences_forward_revision
        ON intelligence_calendar_event_occurrences;
        DROP TRIGGER trg_calendar_events_forward_revision
        ON intelligence_calendar_events;
        DROP TRIGGER trg_calendar_occurrences_state_history
        ON intelligence_calendar_event_occurrences;
        DROP TRIGGER trg_calendar_events_state_history
        ON intelligence_calendar_events;
        DROP FUNCTION calendar_require_forward_revision();
        DROP FUNCTION calendar_require_state_history();
        """
    )
    op.drop_constraint(
        op.f(f"ck_{TRANSITION_TABLE}_legal_transition"),
        TRANSITION_TABLE,
        type_="check",
    )
    op.drop_constraint(
        op.f(f"ck_{TRANSITION_TABLE}_phase1_no_outcome"),
        TRANSITION_TABLE,
        type_="check",
    )
    op.drop_constraint(
        op.f(f"ck_{RULE_TABLE}_all_day_duration"),
        RULE_TABLE,
        type_="check",
    )
    op.drop_constraint(
        op.f(f"ck_{SCHEDULE_TABLE}_timed_time_precision"),
        SCHEDULE_TABLE,
        type_="check",
    )
    op.drop_constraint(
        op.f(f"ck_{SCHEDULE_TABLE}_unknown_precision"),
        SCHEDULE_TABLE,
        type_="check",
    )
