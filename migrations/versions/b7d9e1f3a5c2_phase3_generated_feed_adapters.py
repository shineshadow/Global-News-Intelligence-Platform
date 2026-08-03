"""Register installation-bound RSSHub and RSS-Bridge adapters.

Revision ID: b7d9e1f3a5c2
Revises: a4c2e8f0b6d1
Create Date: 2026-08-03

The migration registers exact generated-feed capabilities. It configures no
internal service, SourceEndpoint, secret, rate policy, or endpoint cutover.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7d9e1f3a5c2"
down_revision: str | Sequence[str] | None = "a4c2e8f0b6d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO acquisition_adapters (
                slug, version, display_name, implementation, status,
                configuration_schema, provenance, activated_at
            )
            VALUES
                (
                    'rsshub',
                    '1',
                    'RSSHub Generated Feed',
                    'ingestion.adapters.generated_feed:RSSHubAdapter',
                    'active',
                    jsonb_build_object(
                        'type', 'object',
                        'properties', jsonb_build_object(
                            'internal_service_identity', jsonb_build_object(
                                'type', 'string', 'minLength', 1
                            )
                        ),
                        'required', jsonb_build_array('internal_service_identity'),
                        'additionalProperties', false
                    ),
                    jsonb_build_object(
                        'migration', 'b7d9e1f3a5c2',
                        'egress_policy', 'installation-registered-internal-v1',
                        'inspection_policy', 'gni-bwrap-seccomp-v1',
                        'activation_scope', 'registry-only-no-service-or-endpoint-configuration'
                    ),
                    now()
                ),
                (
                    'rss_bridge',
                    '1',
                    'RSS-Bridge Generated Feed',
                    'ingestion.adapters.generated_feed:RSSBridgeAdapter',
                    'active',
                    jsonb_build_object(
                        'type', 'object',
                        'properties', jsonb_build_object(
                            'internal_service_identity', jsonb_build_object(
                                'type', 'string', 'minLength', 1
                            )
                        ),
                        'required', jsonb_build_array('internal_service_identity'),
                        'additionalProperties', false
                    ),
                    jsonb_build_object(
                        'migration', 'b7d9e1f3a5c2',
                        'egress_policy', 'installation-registered-internal-v1',
                        'inspection_policy', 'gni-bwrap-seccomp-v1',
                        'activation_scope', 'registry-only-no-service-or-endpoint-configuration'
                    ),
                    now()
                )
            ON CONFLICT (slug, version) DO NOTHING;

            DO $$
            DECLARE
                adapter_row record;
            BEGIN
                FOR adapter_row IN
                    SELECT expected.slug, expected.display_name, expected.implementation
                    FROM (
                        VALUES
                            (
                                'rsshub',
                                'RSSHub Generated Feed',
                                'ingestion.adapters.generated_feed:RSSHubAdapter'
                            ),
                            (
                                'rss_bridge',
                                'RSS-Bridge Generated Feed',
                                'ingestion.adapters.generated_feed:RSSBridgeAdapter'
                            )
                    ) AS expected(slug, display_name, implementation)
                LOOP
                    IF NOT EXISTS (
                        SELECT 1
                        FROM acquisition_adapters AS adapter
                        WHERE adapter.slug = adapter_row.slug
                          AND adapter.version = '1'
                          AND adapter.display_name = adapter_row.display_name
                          AND adapter.implementation = adapter_row.implementation
                          AND adapter.status = 'active'
                          AND adapter.configuration_schema = jsonb_build_object(
                              'type', 'object',
                              'properties', jsonb_build_object(
                                  'internal_service_identity', jsonb_build_object(
                                      'type', 'string', 'minLength', 1
                                  )
                              ),
                              'required', jsonb_build_array('internal_service_identity'),
                              'additionalProperties', false
                          )
                    ) THEN
                        RAISE EXCEPTION
                            'Existing % v1 registration conflicts with the repository implementation',
                            adapter_row.slug;
                    END IF;
                END LOOP;
            END
            $$;

            INSERT INTO acquisition_adapter_compatibilities (
                adapter_id, endpoint_type, endpoint_format,
                acquisition_method, platform, platform_key
            )
            SELECT
                adapter.id,
                'feed',
                format.endpoint_format,
                'feed_parser',
                NULL,
                '*'
            FROM acquisition_adapters AS adapter
            CROSS JOIN (VALUES ('rss'), ('atom')) AS format(endpoint_format)
            WHERE adapter.slug IN ('rsshub', 'rss_bridge')
              AND adapter.version = '1'
            ON CONFLICT DO NOTHING;

            INSERT INTO acquisition_adapter_artifact_capabilities (
                adapter_id, artifact_format_id,
                identification_supported, safe_parser_supported,
                safe_extraction_supported
            )
            SELECT
                adapter.id,
                format.id,
                true,
                true,
                false
            FROM acquisition_adapters AS adapter
            CROSS JOIN artifact_formats AS format
            WHERE adapter.slug IN ('rsshub', 'rss_bridge')
              AND adapter.version = '1'
              AND format.slug IN ('rss', 'atom')
              AND format.is_active
              AND format.is_terminal
            ON CONFLICT DO NOTHING;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                configured_slug text;
            BEGIN
                SELECT adapter.slug INTO configured_slug
                FROM acquisition_endpoint_configurations AS configuration
                JOIN acquisition_adapters AS adapter
                  ON adapter.id = configuration.adapter_id
                WHERE adapter.slug IN ('rsshub', 'rss_bridge')
                  AND adapter.version = '1'
                LIMIT 1;

                IF configured_slug IS NOT NULL THEN
                    RAISE EXCEPTION
                        'Refusing lossless-only generated-feed adapter downgrade: '
                        'endpoint configuration history exists for %',
                        configured_slug;
                END IF;
            END
            $$;

            DELETE FROM acquisition_adapter_artifact_capabilities
            WHERE adapter_id IN (
                SELECT id FROM acquisition_adapters
                WHERE slug IN ('rsshub', 'rss_bridge') AND version = '1'
            );

            DELETE FROM acquisition_adapter_compatibilities
            WHERE adapter_id IN (
                SELECT id FROM acquisition_adapters
                WHERE slug IN ('rsshub', 'rss_bridge') AND version = '1'
            );

            DELETE FROM acquisition_adapters
            WHERE slug IN ('rsshub', 'rss_bridge')
              AND version = '1'
              AND provenance ->> 'migration' = 'b7d9e1f3a5c2';
            """
        )
    )
