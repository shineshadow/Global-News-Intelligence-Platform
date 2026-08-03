"""Register the Phase 3 feed adapter and structural evidence mappings.

Revision ID: f3a1c7d9e2b4
Revises: e4f6a8b0c213
Create Date: 2026-08-03

This migration registers executable RSS/Atom capability without configuring
or cutting over any existing SourceEndpoint.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3a1c7d9e2b4"
down_revision: str | Sequence[str] | None = "e4f6a8b0c213"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO artifact_format_media_types (
                artifact_format_id, media_type, authority_slug,
                is_preferred, provenance
            )
            SELECT
                format.id,
                evidence.media_type,
                evidence.authority_slug,
                evidence.is_preferred,
                jsonb_build_object(
                    'migration', 'f3a1c7d9e2b4',
                    'purpose', 'bounded structural feed identification'
                )
            FROM artifact_formats AS format
            JOIN (
                VALUES
                    ('rss', 'application/rss+xml', 'iana', true),
                    ('rss', 'application/rdf+xml', 'iana', false),
                    ('rss', 'application/xml', 'iana', false),
                    ('rss', 'text/xml', 'iana', false),
                    ('atom', 'application/atom+xml', 'iana', true),
                    ('atom', 'application/xml', 'iana', false),
                    ('atom', 'text/xml', 'iana', false)
            ) AS evidence(format_slug, media_type, authority_slug, is_preferred)
                ON evidence.format_slug = format.slug
            ON CONFLICT DO NOTHING;

            INSERT INTO artifact_format_extensions (
                artifact_format_id, extension, authority_slug,
                is_preferred, provenance
            )
            SELECT
                format.id,
                evidence.extension,
                evidence.authority_slug,
                evidence.is_preferred,
                jsonb_build_object(
                    'migration', 'f3a1c7d9e2b4',
                    'purpose', 'bounded structural feed identification'
                )
            FROM artifact_formats AS format
            JOIN (
                VALUES
                    ('rss', 'rss', 'rss-advisory-board', true),
                    ('rss', 'xml', 'iana', false),
                    ('atom', 'atom', 'ietf-rfc-4287', true),
                    ('atom', 'xml', 'iana', false)
            ) AS evidence(format_slug, extension, authority_slug, is_preferred)
                ON evidence.format_slug = format.slug
            ON CONFLICT DO NOTHING;

            INSERT INTO acquisition_adapters (
                slug, version, display_name, implementation, status,
                configuration_schema, provenance, activated_at
            )
            VALUES (
                'feed_parser',
                '1',
                'RSS and Atom Feed Parser',
                'ingestion.adapters.feed_parser:FeedParserAdapter',
                'active',
                jsonb_build_object(
                    'type', 'object',
                    'properties', '{}'::jsonb,
                    'additionalProperties', false
                ),
                jsonb_build_object(
                    'migration', 'f3a1c7d9e2b4',
                    'egress_policy', 'ip-pinned-public-v1',
                    'inspection_policy', 'gni-bwrap-seccomp-v1',
                    'activation_scope', 'registry-only-no-endpoint-cutover'
                ),
                now()
            )
            ON CONFLICT (slug, version) DO NOTHING;

            DO $$
            DECLARE
                feed_adapter_id bigint;
            BEGIN
                SELECT id INTO feed_adapter_id
                FROM acquisition_adapters
                WHERE slug = 'feed_parser'
                  AND version = '1'
                  AND display_name = 'RSS and Atom Feed Parser'
                  AND implementation =
                      'ingestion.adapters.feed_parser:FeedParserAdapter'
                  AND status = 'active'
                  AND configuration_schema = jsonb_build_object(
                      'type', 'object',
                      'properties', '{}'::jsonb,
                      'additionalProperties', false
                  );

                IF feed_adapter_id IS NULL THEN
                    RAISE EXCEPTION
                        'Existing feed_parser v1 registration conflicts with '
                        'the repository implementation';
                END IF;

                INSERT INTO acquisition_adapter_compatibilities (
                    adapter_id, endpoint_type, endpoint_format,
                    acquisition_method, platform, platform_key
                )
                VALUES
                    (feed_adapter_id, 'feed', 'rss', 'feed_parser', NULL, '*'),
                    (feed_adapter_id, 'feed', 'atom', 'feed_parser', NULL, '*')
                ON CONFLICT DO NOTHING;

                INSERT INTO acquisition_adapter_artifact_capabilities (
                    adapter_id, artifact_format_id,
                    identification_supported, safe_parser_supported,
                    safe_extraction_supported
                )
                SELECT
                    feed_adapter_id,
                    format.id,
                    true,
                    true,
                    false
                FROM artifact_formats AS format
                WHERE format.slug IN ('rss', 'atom')
                  AND format.is_active
                  AND format.is_terminal
                ON CONFLICT DO NOTHING;
            END
            $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DO $$
            DECLARE
                feed_adapter_id bigint;
            BEGIN
                SELECT id INTO feed_adapter_id
                FROM acquisition_adapters
                WHERE slug = 'feed_parser' AND version = '1';

                IF feed_adapter_id IS NOT NULL AND EXISTS (
                    SELECT 1
                    FROM acquisition_endpoint_configurations
                    WHERE acquisition_endpoint_configurations.adapter_id = feed_adapter_id
                ) THEN
                    RAISE EXCEPTION
                        'Refusing lossless-only feed-adapter downgrade: '
                        'endpoint configuration history exists';
                END IF;

                DELETE FROM acquisition_adapter_artifact_capabilities
                WHERE acquisition_adapter_artifact_capabilities.adapter_id = feed_adapter_id;

                DELETE FROM acquisition_adapter_compatibilities
                WHERE acquisition_adapter_compatibilities.adapter_id = feed_adapter_id;

                DELETE FROM acquisition_adapters
                WHERE id = feed_adapter_id
                  AND slug = 'feed_parser'
                  AND version = '1'
                  AND implementation =
                      'ingestion.adapters.feed_parser:FeedParserAdapter';
            END
            $$;

            DELETE FROM artifact_format_extensions
            WHERE provenance ->> 'migration' = 'f3a1c7d9e2b4';

            DELETE FROM artifact_format_media_types
            WHERE provenance ->> 'migration' = 'f3a1c7d9e2b4';
            """
        )
    )
