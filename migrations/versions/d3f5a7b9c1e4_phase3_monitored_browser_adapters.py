"""Register changedetection and Playwright listing adapters.

Revision ID: d3f5a7b9c1e4
Revises: c1e3f5a7b9d2
Create Date: 2026-08-03

The migration is registry-only. It installs no service, browser, endpoint
configuration, secret binding, watch, renderer route, or cutover.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d3f5a7b9c1e4"
down_revision: str | Sequence[str] | None = "c1e3f5a7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        """
        INSERT INTO acquisition_adapters (
            slug, version, display_name, implementation, status,
            configuration_schema, provenance, activated_at
        ) VALUES
            (
                'changedetection', '1', 'changedetection.io Snapshot Listing',
                'ingestion.adapters.monitored_listing:ChangedetectionAdapter', 'active',
                $json${"type":"object","required":["internal_service_identity","snapshot_url","watch_uuid","item_selector","fields"],"additionalProperties":false,"properties":{"internal_service_identity":{"type":"string","minLength":1},"snapshot_url":{"type":"string","format":"uri","pattern":"^https?://"},"watch_uuid":{"type":"string","minLength":1},"item_selector":{"type":"string","minLength":1},"fields":{"$ref":"#/$defs/fields"}},"$defs":{"field":{"type":"object","required":["selector"],"additionalProperties":false,"properties":{"selector":{"type":"string","minLength":1},"attribute":{"type":"string","minLength":1}}},"fields":{"type":"object","required":["url","title"],"additionalProperties":false,"properties":{"url":{"$ref":"#/$defs/field"},"title":{"$ref":"#/$defs/field"},"summary":{"$ref":"#/$defs/field"},"published_at":{"$ref":"#/$defs/field"},"external_id":{"$ref":"#/$defs/field"},"author":{"$ref":"#/$defs/field"},"language":{"$ref":"#/$defs/field"}}}}}$json$::jsonb,
                $json${"migration":"d3f5a7b9c1e4","egress_policy":"installation-registered-internal-v1","service_contract":"changedetection-snapshot-v1","inspection_policy":"gni-bwrap-seccomp-v1","activation_scope":"registry-only-no-service-watch-endpoint-or-cutover"}$json$::jsonb,
                now()
            ),
            (
                'playwright', '1', 'Playwright Rendered Listing Fallback',
                'ingestion.adapters.monitored_listing:PlaywrightAdapter', 'active',
                $json${"type":"object","required":["internal_service_identity","render_url","wait_strategy","timeout_seconds","item_selector","fields"],"additionalProperties":false,"properties":{"internal_service_identity":{"type":"string","minLength":1},"render_url":{"type":"string","format":"uri","pattern":"^https?://"},"wait_strategy":{"type":"string","enum":["domcontentloaded","networkidle"]},"timeout_seconds":{"type":"integer","minimum":1,"maximum":60},"item_selector":{"type":"string","minLength":1},"fields":{"$ref":"#/$defs/fields"}},"$defs":{"field":{"type":"object","required":["selector"],"additionalProperties":false,"properties":{"selector":{"type":"string","minLength":1},"attribute":{"type":"string","minLength":1}}},"fields":{"type":"object","required":["url","title"],"additionalProperties":false,"properties":{"url":{"$ref":"#/$defs/field"},"title":{"$ref":"#/$defs/field"},"summary":{"$ref":"#/$defs/field"},"published_at":{"$ref":"#/$defs/field"},"external_id":{"$ref":"#/$defs/field"},"author":{"$ref":"#/$defs/field"},"language":{"$ref":"#/$defs/field"}}}}}$json$::jsonb,
                $json${"migration":"d3f5a7b9c1e4","egress_policy":"installation-registered-internal-v1","service_contract":"playwright-disposable-v1","inspection_policy":"gni-bwrap-seccomp-v1","activation_scope":"registry-only-no-service-route-endpoint-or-cutover"}$json$::jsonb,
                now()
            )
        ON CONFLICT (slug, version) DO NOTHING;

        INSERT INTO acquisition_adapter_compatibilities (
            adapter_id, endpoint_type, endpoint_format,
            acquisition_method, platform, platform_key
        )
        SELECT adapter.id, 'website', 'html', expected.method, NULL, '*'
        FROM acquisition_adapters AS adapter
        JOIN (VALUES
            ('changedetection', 'web_scraper'),
            ('playwright', 'browser_automation')
        ) AS expected(slug, method) ON expected.slug = adapter.slug
        WHERE adapter.version = '1'
        ON CONFLICT DO NOTHING;

        INSERT INTO acquisition_adapter_artifact_capabilities (
            adapter_id, artifact_format_id, identification_supported,
            safe_parser_supported, safe_extraction_supported
        )
        SELECT adapter.id, format.id, true, true, true
        FROM acquisition_adapters AS adapter
        CROSS JOIN artifact_formats AS format
        WHERE adapter.slug IN ('changedetection', 'playwright')
          AND adapter.version = '1' AND format.slug = 'html'
          AND format.is_active AND format.is_terminal
        ON CONFLICT DO NOTHING;

        INSERT INTO acquisition_adapter_secret_slots (
            adapter_id, slot_name, is_required,
            authentication_types, permitted_scopes
        )
        SELECT adapter.id, 'api_key', true,
               ARRAY['api_key_header']::varchar[],
               ARRAY['installation']::varchar[]
        FROM acquisition_adapters AS adapter
        WHERE adapter.slug IN ('changedetection', 'playwright')
          AND adapter.version = '1'
        ON CONFLICT DO NOTHING;

        DO $$
        BEGIN
            IF (SELECT count(*) FROM acquisition_adapters
                WHERE slug IN ('changedetection', 'playwright')
                  AND version = '1' AND status = 'active') <> 2 THEN
                RAISE EXCEPTION 'Monitored/browser adapter registration conflicts with repository state';
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
                WHERE adapter.slug IN ('changedetection', 'playwright')
                  AND adapter.version = '1'
            ) OR EXISTS (
                SELECT 1 FROM acquisition_secret_bindings AS binding
                JOIN acquisition_adapter_secret_slots AS slot
                  ON slot.id = binding.adapter_secret_slot_id
                JOIN acquisition_adapters AS adapter ON adapter.id = slot.adapter_id
                WHERE adapter.slug IN ('changedetection', 'playwright')
                  AND adapter.version = '1'
            ) THEN
                RAISE EXCEPTION
                    'Refusing lossless-only monitored/browser downgrade: configuration or secret-binding history exists';
            END IF;
        END $$;
        DELETE FROM acquisition_adapter_secret_slots WHERE adapter_id IN (
            SELECT id FROM acquisition_adapters
            WHERE slug IN ('changedetection', 'playwright') AND version = '1'
        );
        DELETE FROM acquisition_adapter_artifact_capabilities WHERE adapter_id IN (
            SELECT id FROM acquisition_adapters
            WHERE slug IN ('changedetection', 'playwright') AND version = '1'
        );
        DELETE FROM acquisition_adapter_compatibilities WHERE adapter_id IN (
            SELECT id FROM acquisition_adapters
            WHERE slug IN ('changedetection', 'playwright') AND version = '1'
        );
        DELETE FROM acquisition_adapters
        WHERE slug IN ('changedetection', 'playwright') AND version = '1'
          AND provenance ->> 'migration' = 'd3f5a7b9c1e4';
        """
    )
