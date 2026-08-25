"""Bind generated-feed adapters to an exact publisher robots target.

Revision ID: a7c9e1f3b5d4
Revises: e5a7c9d1f3b2
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c9e1f3b5d4"
down_revision: str | None = "e5a7c9d1f3b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _schema(*, publisher_target: bool) -> str:
    publisher_property = (
        ", 'publisher_target_url', jsonb_build_object("
        "'type', 'string', 'minLength', 1, 'maxLength', 8192, "
        "'pattern', '^https?://')"
        if publisher_target
        else ""
    )
    required = (
        "jsonb_build_array('internal_service_identity', 'publisher_target_url')"
        if publisher_target
        else "jsonb_build_array('internal_service_identity')"
    )
    return f"""
        jsonb_build_object(
            'type', 'object',
            'properties', jsonb_build_object(
                'internal_service_identity', jsonb_build_object(
                    'type', 'string', 'minLength', 1
                )
                {publisher_property}
            ),
            'required', {required},
            'additionalProperties', false
        )
    """


def upgrade() -> None:
    connection = op.get_bind()
    incompatible = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM acquisition_endpoint_configurations AS configuration
                JOIN acquisition_adapters AS adapter
                  ON adapter.id = configuration.adapter_id
                WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                  AND adapter.version = '1'
                  AND (
                      jsonb_typeof(configuration.configuration -> 'publisher_target_url')
                          IS DISTINCT FROM 'string'
                      OR btrim(configuration.configuration ->> 'publisher_target_url') = ''
                  )
            )
            """
        )
    ).scalar_one()
    if incompatible:
        raise RuntimeError(
            "Cannot activate Proof 34B while a generated-feed configuration lacks "
            "its exact publisher_target_url. Update and review those targets first."
        )

    op.execute(
        sa.text(
            f"""
            UPDATE acquisition_adapters
            SET configuration_schema = {_schema(publisher_target=True)},
                provenance = provenance || jsonb_build_object(
                    'robots_target_binding', 'publisher-target-url-v1',
                    'proof_34b_migration', 'a7c9e1f3b5d4'
                )
            WHERE slug IN ('rsshub', 'rss_bridge')
              AND version = '1'
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    retained = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM acquisition_endpoint_configurations AS configuration
                JOIN acquisition_adapters AS adapter
                  ON adapter.id = configuration.adapter_id
                WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                  AND adapter.version = '1'
            )
            """
        )
    ).scalar_one()
    if retained:
        raise RuntimeError(
            "Cannot downgrade Proof 34B while generated-feed publisher target "
            "configurations are retained."
        )
    op.execute(
        sa.text(
            f"""
            UPDATE acquisition_adapters
            SET configuration_schema = {_schema(publisher_target=False)},
                provenance = provenance - 'robots_target_binding' - 'proof_34b_migration'
            WHERE slug IN ('rsshub', 'rss_bridge')
              AND version = '1'
            """
        )
    )
