"""harden Step 25 revision and match provenance invariants

Revision ID: c25f4a7b9d02
Revises: b25c7d9e1f30
Create Date: 2026-07-27

Seal Monitor revisions at the database boundary and require match evaluation
provenance to belong to the same Monitor.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c25f4a7b9d02"
down_revision: str | Sequence[str] | None = "b25c7d9e1f30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SELECTOR_TABLES = (
    "monitor_revision_geographies",
    "monitor_revision_topics",
    "monitor_revision_entities",
    "monitor_revision_entity_roles",
    "monitor_revision_document_types",
    "monitor_revision_content_formats",
    "monitor_revision_sources",
    "monitor_revision_source_types",
    "monitor_revision_languages",
)

OLD_FIRST_RUN_FK = "fk_monitor_matches_first_evaluation_run_id_monitor_eval_1c46"
OLD_LAST_RUN_FK = "fk_monitor_matches_last_evaluation_run_id_monitor_evalu_fb3b"


def _require_consistent_existing_hierarchy_policies() -> None:
    mixed_count = op.get_bind().execute(
        sa.text(
            """
            SELECT count(*)
            FROM (
                SELECT revision_id
                FROM monitor_revision_geographies
                GROUP BY revision_id
                HAVING count(DISTINCT include_descendants) > 1
                UNION ALL
                SELECT revision_id
                FROM monitor_revision_topics
                GROUP BY revision_id
                HAVING count(DISTINCT include_descendants) > 1
                UNION ALL
                SELECT revision_id
                FROM monitor_revision_document_types
                GROUP BY revision_id
                HAVING count(DISTINCT include_descendants) > 1
                UNION ALL
                SELECT revision_id
                FROM monitor_revision_source_types
                GROUP BY revision_id
                HAVING count(DISTINCT include_descendants) > 1
            ) AS mixed_policies
            """
        )
    ).scalar_one()
    if mixed_count:
        raise RuntimeError(
            "Step 25 freeze hardening found "
            f"{mixed_count} revision hierarchy dimension(s) with mixed "
            "descendant policy."
        )


def _seal_revisions() -> None:
    _require_consistent_existing_hierarchy_policies()
    op.add_column(
        "monitor_revisions",
        sa.Column(
            "sealed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE monitor_revisions
        SET sealed_at = created_at
        WHERE sealed_at IS NULL;

        CREATE FUNCTION preserve_monitor_revision_immutability()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            inconsistent_hierarchy boolean;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.sealed_at IS NOT NULL THEN
                    RAISE EXCEPTION
                        'sealed Monitor revisions cannot be deleted';
                END IF;
                RETURN OLD;
            END IF;

            IF OLD.sealed_at IS NOT NULL THEN
                RAISE EXCEPTION
                    'sealed Monitor revisions cannot be updated';
            END IF;
            IF NEW.sealed_at IS NULL THEN
                RAISE EXCEPTION
                    'the only permitted Monitor revision update is sealing';
            END IF;
            IF (
                NEW.id,
                NEW.monitor_id,
                NEW.revision_number,
                NEW.criteria_version,
                NEW.minimum_confidence,
                NEW.effective_from,
                NEW.text_query,
                NEW.match_all_in_profile,
                NEW.change_reason,
                NEW.created_at
            ) IS DISTINCT FROM (
                OLD.id,
                OLD.monitor_id,
                OLD.revision_number,
                OLD.criteria_version,
                OLD.minimum_confidence,
                OLD.effective_from,
                OLD.text_query,
                OLD.match_all_in_profile,
                OLD.change_reason,
                OLD.created_at
            ) THEN
                RAISE EXCEPTION
                    'Monitor revision criteria cannot change while sealing';
            END IF;

            SELECT EXISTS (
                SELECT 1
                FROM (
                    SELECT revision_id
                    FROM monitor_revision_geographies
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                    UNION ALL
                    SELECT revision_id
                    FROM monitor_revision_topics
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                    UNION ALL
                    SELECT revision_id
                    FROM monitor_revision_document_types
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                    UNION ALL
                    SELECT revision_id
                    FROM monitor_revision_source_types
                    WHERE revision_id = NEW.id
                    GROUP BY revision_id
                    HAVING count(DISTINCT include_descendants) > 1
                ) AS mixed_policies
            ) INTO inconsistent_hierarchy;
            IF inconsistent_hierarchy THEN
                RAISE EXCEPTION
                    'one Monitor hierarchy dimension cannot mix descendant policies';
            END IF;

            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER monitor_revisions_preserve_immutability
        BEFORE UPDATE OR DELETE
        ON monitor_revisions
        FOR EACH ROW
        EXECUTE FUNCTION preserve_monitor_revision_immutability();

        CREATE FUNCTION require_monitor_revisions_sealed()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM monitor_revisions
                WHERE sealed_at IS NULL
            ) THEN
                RAISE EXCEPTION
                    'every Monitor revision must be sealed before commit';
            END IF;
            RETURN NULL;
        END;
        $$;

        CREATE CONSTRAINT TRIGGER monitor_revisions_require_seal
        AFTER INSERT OR UPDATE OF sealed_at
        ON monitor_revisions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION require_monitor_revisions_sealed();

        CREATE FUNCTION preserve_monitor_revision_selectors()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            old_sealed timestamptz;
            new_sealed timestamptz;
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                SELECT sealed_at INTO old_sealed
                FROM monitor_revisions
                WHERE id = OLD.revision_id;
                IF old_sealed IS NOT NULL THEN
                    RAISE EXCEPTION
                        'selectors of sealed Monitor revisions cannot change';
                END IF;
            END IF;
            IF TG_OP IN ('INSERT', 'UPDATE') THEN
                SELECT sealed_at INTO new_sealed
                FROM monitor_revisions
                WHERE id = NEW.revision_id;
                IF new_sealed IS NOT NULL THEN
                    RAISE EXCEPTION
                        'selectors cannot be added to a sealed Monitor revision';
                END IF;
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$;
        """
    )
    for table_name in SELECTOR_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table_name}_preserve_immutability
            BEFORE INSERT OR UPDATE OR DELETE
            ON {table_name}
            FOR EACH ROW
            EXECUTE FUNCTION preserve_monitor_revision_selectors();
            """
        )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION require_monitor_current_revision()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM monitors AS monitor
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM monitor_revisions AS revision
                    WHERE revision.monitor_id = monitor.id
                      AND revision.revision_number =
                          monitor.current_revision_number
                      AND revision.sealed_at IS NOT NULL
                )
            ) THEN
                RAISE EXCEPTION
                    'every monitor must reference an existing sealed current revision';
            END IF;
            RETURN NULL;
        END;
        $$;
        """
    )


def _bind_match_runs_to_monitor() -> None:
    bind = op.get_bind()
    invalid_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
            FROM monitor_matches AS match
            LEFT JOIN monitor_evaluation_runs AS first_run
              ON first_run.id = match.first_evaluation_run_id
            LEFT JOIN monitor_evaluation_runs AS last_run
              ON last_run.id = match.last_evaluation_run_id
            WHERE (
                match.first_evaluation_run_id IS NOT NULL
                AND first_run.monitor_id IS DISTINCT FROM match.monitor_id
            ) OR (
                match.last_evaluation_run_id IS NOT NULL
                AND last_run.monitor_id IS DISTINCT FROM match.monitor_id
            )
            """
        )
    ).scalar_one()
    if invalid_count:
        raise RuntimeError(
            "Step 25 freeze hardening found "
            f"{invalid_count} cross-Monitor evaluation reference(s)."
        )

    op.create_unique_constraint(
        "uq_monitor_evaluation_runs_monitor_id",
        "monitor_evaluation_runs",
        ["monitor_id", "id"],
    )
    op.drop_constraint(
        OLD_FIRST_RUN_FK,
        "monitor_matches",
        type_="foreignkey",
    )
    op.drop_constraint(
        OLD_LAST_RUN_FK,
        "monitor_matches",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_monitor_matches_first_evaluation_run",
        "monitor_matches",
        "monitor_evaluation_runs",
        ["monitor_id", "first_evaluation_run_id"],
        ["monitor_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_monitor_matches_last_evaluation_run",
        "monitor_matches",
        "monitor_evaluation_runs",
        ["monitor_id", "last_evaluation_run_id"],
        ["monitor_id", "id"],
        ondelete="RESTRICT",
    )


def upgrade() -> None:
    _seal_revisions()
    _bind_match_runs_to_monitor()


def _require_empty_monitor_subsystem() -> None:
    monitor_count = op.get_bind().execute(sa.text("SELECT count(*) FROM monitors")).scalar_one()
    if monitor_count:
        raise RuntimeError(
            "Step 25 freeze-hardening downgrade would remove immutable-history "
            f"protections for {monitor_count} Monitor row(s)."
        )


def downgrade() -> None:
    _require_empty_monitor_subsystem()

    op.drop_constraint(
        "fk_monitor_matches_last_evaluation_run",
        "monitor_matches",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_monitor_matches_first_evaluation_run",
        "monitor_matches",
        type_="foreignkey",
    )
    op.create_foreign_key(
        OLD_FIRST_RUN_FK,
        "monitor_matches",
        "monitor_evaluation_runs",
        ["first_evaluation_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        OLD_LAST_RUN_FK,
        "monitor_matches",
        "monitor_evaluation_runs",
        ["last_evaluation_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "uq_monitor_evaluation_runs_monitor_id",
        "monitor_evaluation_runs",
        type_="unique",
    )

    for table_name in reversed(SELECTOR_TABLES):
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS
                {table_name}_preserve_immutability
            ON {table_name};
            """
        )
    op.execute(
        """
        DROP TRIGGER IF EXISTS monitor_revisions_require_seal
        ON monitor_revisions;
        DROP TRIGGER IF EXISTS monitor_revisions_preserve_immutability
        ON monitor_revisions;
        DROP FUNCTION IF EXISTS preserve_monitor_revision_selectors();
        DROP FUNCTION IF EXISTS require_monitor_revisions_sealed();
        DROP FUNCTION IF EXISTS preserve_monitor_revision_immutability();

        CREATE OR REPLACE FUNCTION require_monitor_current_revision()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM monitors AS monitor
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM monitor_revisions AS revision
                    WHERE revision.monitor_id = monitor.id
                      AND revision.revision_number =
                          monitor.current_revision_number
                )
            ) THEN
                RAISE EXCEPTION
                    'every monitor must reference an existing current revision';
            END IF;
            RETURN NULL;
        END;
        $$;
        """
    )
    op.drop_column("monitor_revisions", "sealed_at")
