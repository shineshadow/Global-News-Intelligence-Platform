"""Remove the retired Proof 34 robots subsystem.

Revision ID: d9e1f3a5b7c9
Revises: b8d0f2a4c6e8
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9e1f3a5b7c9"
down_revision: str | None = "b8d0f2a4c6e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _generated_feed_schema() -> str:
    return """
        jsonb_build_object(
            'type', 'object',
            'properties', jsonb_build_object(
                'internal_service_identity', jsonb_build_object(
                    'type', 'string', 'minLength', 1
                )
            ),
            'required', jsonb_build_array('internal_service_identity'),
            'additionalProperties', false
        )
    """


def upgrade() -> None:
    connection = op.get_bind()

    op.execute("DROP TABLE acquisition_robots_gates")
    op.execute("DROP TABLE acquisition_robots_evaluations")
    op.execute("DROP TABLE acquisition_robots_snapshots")
    op.execute("DROP FUNCTION IF EXISTS phase3_validate_robots_gate()")
    op.execute("DROP FUNCTION IF EXISTS phase3_validate_robots_evaluation()")
    op.execute("DROP FUNCTION IF EXISTS phase3_validate_robots_snapshot()")
    op.execute("DROP FUNCTION IF EXISTS phase3_robots_reject_immutable_mutation()")

    op.execute("DROP TRIGGER owner_policy_events_no_update_delete ON owner_policy_override_events")
    op.execute("DROP TRIGGER owner_policy_overrides_no_delete ON owner_policy_overrides")
    op.execute(
        """
        DELETE FROM owner_policy_override_events
        WHERE override_id IN (
            SELECT id FROM owner_policy_overrides
            WHERE policy_key LIKE 'acquisition.robots.%'
        )
        """
    )
    op.execute("DELETE FROM owner_policy_overrides WHERE policy_key LIKE 'acquisition.robots.%'")
    op.execute(
        """
        CREATE TRIGGER owner_policy_events_no_update_delete
        BEFORE UPDATE OR DELETE ON owner_policy_override_events
        FOR EACH ROW EXECUTE FUNCTION prevent_owner_policy_event_mutation();

        CREATE TRIGGER owner_policy_overrides_no_delete
        BEFORE DELETE ON owner_policy_overrides
        FOR EACH ROW EXECUTE FUNCTION prevent_owner_policy_override_delete();
        """
    )

    op.execute(
        "DROP TRIGGER trg_rate_observations_append_only ON acquisition_rate_limit_observations"
    )
    op.execute("DELETE FROM acquisition_rate_limit_observations WHERE observation_type = 'robots'")
    op.drop_constraint(
        op.f("ck_acquisition_rate_limit_observations_observation_type"),
        "acquisition_rate_limit_observations",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_rate_limit_observations_observation_type"),
        "acquisition_rate_limit_observations",
        "observation_type IN ('http_status', 'retry_after', 'provider_quota', 'provider_reset')",
    )
    op.execute(
        """
        CREATE TRIGGER trg_rate_observations_append_only
        BEFORE UPDATE OR DELETE ON acquisition_rate_limit_observations
        FOR EACH ROW EXECUTE FUNCTION prevent_acquisition_append_only_mutation();
        """
    )

    op.drop_column("acquisition_rate_limit_buckets", "robots_disallow_until")
    op.execute(
        "UPDATE acquisition_rate_limit_policies SET mode = 'conservative' "
        "WHERE mode = 'robots_aware'"
    )
    op.drop_constraint(
        op.f("ck_acquisition_rate_limit_policies_mode"),
        "acquisition_rate_limit_policies",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_rate_limit_policies_mode"),
        "acquisition_rate_limit_policies",
        "mode IN ('provider_defined', 'conservative', 'custom')",
    )

    op.execute(
        sa.text(
            """
            UPDATE acquisition_endpoint_configurations AS configuration
            SET configuration = configuration.configuration - 'publisher_target_url'
            FROM acquisition_adapters AS adapter
            WHERE adapter.id = configuration.adapter_id
              AND adapter.slug IN ('rsshub', 'rss_bridge')
              AND adapter.version = '1'
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE acquisition_adapters
            SET configuration_schema = {_generated_feed_schema()},
                provenance = provenance - 'robots_target_binding' - 'proof_34b_migration'
            WHERE slug IN ('rsshub', 'rss_bridge')
              AND version = '1'
            """
        )
    )

    remaining = connection.execute(
        sa.text(
            "SELECT count(*) FROM owner_policy_overrides "
            "WHERE policy_key LIKE 'acquisition.robots.%'"
        )
    ).scalar_one()
    if remaining:
        raise RuntimeError("Proof 34 Owner-policy state remains after cleanup.")


def downgrade() -> None:
    """Restore the empty historical schema shape, never deleted Proof 34 data."""
    from migrations.versions import (
        a7c9e1f3b5d4_proof34b_generated_feed_target_binding as target_binding,
    )
    from migrations.versions import (
        c2f4a6b8d0e1_phase3_robots_evidence_foundation as evidence_foundation,
    )
    from migrations.versions import (
        e5a7c9d1f3b2_proof34a1_unavailable_information_contract as information_contract,
    )

    op.add_column(
        "acquisition_rate_limit_buckets",
        sa.Column("robots_disallow_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint(
        op.f("ck_acquisition_rate_limit_observations_observation_type"),
        "acquisition_rate_limit_observations",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_rate_limit_observations_observation_type"),
        "acquisition_rate_limit_observations",
        "observation_type IN ('http_status', 'retry_after', 'provider_quota', "
        "'provider_reset', 'robots')",
    )
    op.drop_constraint(
        op.f("ck_acquisition_rate_limit_policies_mode"),
        "acquisition_rate_limit_policies",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_rate_limit_policies_mode"),
        "acquisition_rate_limit_policies",
        "mode IN ('provider_defined', 'robots_aware', 'conservative', 'custom')",
    )

    evidence_foundation.upgrade()
    information_contract.upgrade()

    op.execute(
        sa.text(
            f"""
            UPDATE acquisition_adapters
            SET configuration_schema = {target_binding._schema(publisher_target=True)},
                provenance = provenance || jsonb_build_object(
                    'robots_target_binding', 'publisher-target-url-v1',
                    'proof_34b_migration', 'a7c9e1f3b5d4'
                )
            WHERE slug IN ('rsshub', 'rss_bridge')
              AND version = '1'
            """
        )
    )
