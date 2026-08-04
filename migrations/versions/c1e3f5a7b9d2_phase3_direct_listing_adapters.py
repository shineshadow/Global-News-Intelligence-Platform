"""Register direct JSON/API and HTML listing adapters.

Revision ID: c1e3f5a7b9d2
Revises: b7d9e1f3a5c2
Create Date: 2026-08-03

This migration registers capabilities only. It creates no endpoint
configuration, cutover, credential, or rate-policy state.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "c1e3f5a7b9d2"
down_revision: str | Sequence[str] | None = "b7d9e1f3a5c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
            INSERT INTO artifact_format_media_types (
                artifact_format_id, media_type, authority_slug,
                is_preferred, provenance
            )
            SELECT format.id, evidence.media_type, 'iana', evidence.is_preferred,
                   jsonb_build_object('migration', 'c1e3f5a7b9d2')
            FROM artifact_formats AS format
            JOIN (VALUES
                ('html', 'text/html', true),
                ('html', 'application/xhtml+xml', false),
                ('json', 'application/json', true)
            ) AS evidence(format_slug, media_type, is_preferred)
              ON evidence.format_slug = format.slug
            ON CONFLICT DO NOTHING;

            INSERT INTO artifact_format_extensions (
                artifact_format_id, extension, authority_slug,
                is_preferred, provenance
            )
            SELECT format.id, evidence.extension, evidence.authority_slug,
                   evidence.is_preferred,
                   jsonb_build_object('migration', 'c1e3f5a7b9d2')
            FROM artifact_formats AS format
            JOIN (VALUES
                ('html', 'html', 'iana', true),
                ('html', 'htm', 'iana', false),
                ('json', 'json', 'ietf-rfc-8259', true)
            ) AS evidence(format_slug, extension, authority_slug, is_preferred)
              ON evidence.format_slug = format.slug
            ON CONFLICT DO NOTHING;

            INSERT INTO acquisition_adapters (
                slug, version, display_name, implementation, status,
                configuration_schema, provenance, activated_at
            )
            VALUES
                (
                    'direct_json_api', '1', 'Direct JSON API Listing',
                    'ingestion.adapters.direct_listing:DirectJSONAPIAdapter', 'active',
                    $json${"type":"object","required":["items_path","fields"],"additionalProperties":false,"properties":{"items_path":{"type":"array","minItems":1,"maxItems":16,"items":{"type":"string","minLength":1}},"fields":{"type":"object","required":["url","title"],"additionalProperties":false,"properties":{"url":{"$ref":"#/$defs/path"},"title":{"$ref":"#/$defs/path"},"summary":{"$ref":"#/$defs/path"},"published_at":{"$ref":"#/$defs/path"},"external_id":{"$ref":"#/$defs/path"},"author":{"$ref":"#/$defs/path"},"language":{"$ref":"#/$defs/path"}}}},"$defs":{"path":{"type":"array","minItems":1,"maxItems":16,"items":{"type":"string","minLength":1}}}}$json$::jsonb,
                    $json${"migration":"c1e3f5a7b9d2","egress_policy":"ip-pinned-public-v1","inspection_policy":"gni-bwrap-seccomp-v1","activation_scope":"registry-only-no-endpoint-configuration"}$json$::jsonb,
                    now()
                ),
                (
                    'html_listing', '1', 'Direct HTML Listing',
                    'ingestion.adapters.direct_listing:HTMLListingAdapter', 'active',
                    $json${"type":"object","required":["item_selector","fields"],"additionalProperties":false,"properties":{"item_selector":{"type":"string","minLength":1},"fields":{"type":"object","required":["url","title"],"additionalProperties":false,"properties":{"url":{"$ref":"#/$defs/field"},"title":{"$ref":"#/$defs/field"},"summary":{"$ref":"#/$defs/field"},"published_at":{"$ref":"#/$defs/field"},"external_id":{"$ref":"#/$defs/field"},"author":{"$ref":"#/$defs/field"},"language":{"$ref":"#/$defs/field"}}}},"$defs":{"field":{"type":"object","required":["selector"],"additionalProperties":false,"properties":{"selector":{"type":"string"},"attribute":{"type":"string"}}}}}$json$::jsonb,
                    $json${"migration":"c1e3f5a7b9d2","egress_policy":"ip-pinned-public-v1","inspection_policy":"gni-bwrap-seccomp-v1","activation_scope":"registry-only-no-endpoint-configuration"}$json$::jsonb,
                    now()
                )
            ON CONFLICT (slug, version) DO NOTHING;

            INSERT INTO acquisition_adapter_compatibilities (
                adapter_id, endpoint_type, endpoint_format,
                acquisition_method, platform, platform_key
            )
            SELECT adapter.id, expected.endpoint_type, expected.endpoint_format,
                   expected.acquisition_method, NULL, '*'
            FROM acquisition_adapters AS adapter
            JOIN (VALUES
                ('direct_json_api', 'api', 'json', 'api_client'),
                ('html_listing', 'website', 'html', 'web_scraper')
            ) AS expected(slug, endpoint_type, endpoint_format, acquisition_method)
              ON expected.slug = adapter.slug
            WHERE adapter.version = '1'
            ON CONFLICT DO NOTHING;

            INSERT INTO acquisition_adapter_artifact_capabilities (
                adapter_id, artifact_format_id, identification_supported,
                safe_parser_supported, safe_extraction_supported
            )
            SELECT adapter.id, format.id, true, true, true
            FROM acquisition_adapters AS adapter
            JOIN (VALUES
                ('direct_json_api', 'json'), ('html_listing', 'html')
            ) AS expected(adapter_slug, format_slug) ON expected.adapter_slug = adapter.slug
            JOIN artifact_formats AS format ON format.slug = expected.format_slug
            WHERE adapter.version = '1' AND format.is_active AND format.is_terminal
            ON CONFLICT DO NOTHING;

            DO $$
            BEGIN
                IF (SELECT count(*) FROM acquisition_adapters
                    WHERE slug IN ('direct_json_api', 'html_listing') AND version = '1'
                      AND status = 'active') <> 2 THEN
                    RAISE EXCEPTION 'Direct listing adapter registration conflicts with repository state';
                END IF;
            END $$;
            """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM acquisition_endpoint_configurations AS configuration
                    JOIN acquisition_adapters AS adapter ON adapter.id = configuration.adapter_id
                    WHERE adapter.slug IN ('direct_json_api', 'html_listing')
                      AND adapter.version = '1'
                ) THEN
                    RAISE EXCEPTION
                        'Refusing lossless-only direct listing downgrade: configuration history exists';
                END IF;
            END $$;
            DELETE FROM acquisition_adapter_artifact_capabilities WHERE adapter_id IN (
                SELECT id FROM acquisition_adapters
                WHERE slug IN ('direct_json_api', 'html_listing') AND version = '1'
            );
            DELETE FROM acquisition_adapter_compatibilities WHERE adapter_id IN (
                SELECT id FROM acquisition_adapters
                WHERE slug IN ('direct_json_api', 'html_listing') AND version = '1'
            );
            DELETE FROM acquisition_adapters
            WHERE slug IN ('direct_json_api', 'html_listing') AND version = '1'
              AND provenance ->> 'migration' = 'c1e3f5a7b9d2';
            DELETE FROM artifact_format_extensions
            WHERE provenance ->> 'migration' = 'c1e3f5a7b9d2';
            DELETE FROM artifact_format_media_types
            WHERE provenance ->> 'migration' = 'c1e3f5a7b9d2';
            """
    )
