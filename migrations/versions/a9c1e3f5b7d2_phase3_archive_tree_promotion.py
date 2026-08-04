"""Enable immutable recursive Artifact-tree provenance.

Revision ID: a9c1e3f5b7d2
Revises: f6a8c2d4e901
Create Date: 2026-08-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9c1e3f5b7d2"
down_revision: str | None = "f6a8c2d4e901"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_acquisition_artifacts_resource_payload",
        "acquisition_artifacts",
        type_="unique",
    )
    op.create_index(
        "uq_acquisition_artifacts_root_resource_payload",
        "acquisition_artifacts",
        ["source_endpoint_id", "resource_identity", "payload_id"],
        unique=True,
        postgresql_where=sa.text("parent_artifact_id IS NULL"),
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION phase3_validate_acquisition_artifact()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            prior acquisition_artifacts%ROWTYPE;
            parent acquisition_artifacts%ROWTYPE;
            release_status text;
        BEGIN
            SELECT status INTO STRICT release_status
            FROM artifact_signature_releases
            WHERE id = NEW.signature_release_id
            FOR KEY SHARE;
            IF release_status <> 'active' THEN
                RAISE EXCEPTION
                    'Accepted Artifact requires the active signature release';
            END IF;

            IF NEW.parent_artifact_id IS NOT NULL THEN
                SELECT * INTO STRICT parent
                FROM acquisition_artifacts
                WHERE id = NEW.parent_artifact_id
                FOR KEY SHARE;
                IF parent.id >= NEW.id
                   OR parent.source_endpoint_id <> NEW.source_endpoint_id
                THEN
                    RAISE EXCEPTION
                        'Artifact parent must be earlier and belong to the same endpoint';
                END IF;
            END IF;

            IF NEW.supersedes_artifact_id IS NOT NULL THEN
                SELECT * INTO STRICT prior
                FROM acquisition_artifacts
                WHERE id = NEW.supersedes_artifact_id
                FOR KEY SHARE;
                IF prior.id >= NEW.id
                   OR prior.source_endpoint_id <> NEW.source_endpoint_id
                   OR prior.resource_identity <> NEW.resource_identity
                   OR prior.member_path IS DISTINCT FROM NEW.member_path
                   OR prior.payload_id = NEW.payload_id
                THEN
                    RAISE EXCEPTION
                        'Artifact supersession must be forward-only within one '
                        'resource/member scope and use changed accepted bytes';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        INSERT INTO artifact_format_extensions (
            artifact_format_id, extension, authority_slug, is_preferred, provenance
        )
        SELECT f.id, values.extension, values.authority_slug, true,
               '{"source":"migration:a9c1e3f5b7d2"}'::jsonb
        FROM (
            VALUES ('zip', 'zip', 'iana'), ('tar', 'tar', 'posix')
        ) AS values(format_slug, extension, authority_slug)
        JOIN artifact_formats f ON f.slug = values.format_slug
        WHERE NOT EXISTS (
            SELECT 1 FROM artifact_format_extensions existing
            WHERE existing.artifact_format_id = f.id
              AND existing.extension = values.extension
              AND existing.is_active
        )
        """
    )
    op.execute(
        """
        INSERT INTO artifact_format_media_types (
            artifact_format_id, media_type, authority_slug, is_preferred, provenance
        )
        SELECT f.id, values.media_type, values.authority_slug, true,
               '{"source":"migration:a9c1e3f5b7d2"}'::jsonb
        FROM (
            VALUES ('zip', 'application/zip', 'iana'),
                   ('tar', 'application/x-tar', 'iana')
        ) AS values(format_slug, media_type, authority_slug)
        JOIN artifact_formats f ON f.slug = values.format_slug
        WHERE NOT EXISTS (
            SELECT 1 FROM artifact_format_media_types existing
            WHERE existing.artifact_format_id = f.id
              AND existing.media_type = values.media_type
              AND existing.is_active
        )
        """
    )


def downgrade() -> None:
    connection = op.get_bind()
    conflict = connection.execute(
        sa.text(
            """
            SELECT 1
            FROM acquisition_artifacts
            GROUP BY source_endpoint_id, resource_identity, payload_id
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if conflict is not None:
        raise RuntimeError(
            "Cannot downgrade archive-tree provenance while repeated nested payload "
            "identities exist."
        )
    op.execute(
        "DELETE FROM artifact_format_media_types "
        'WHERE provenance = \'{"source":"migration:a9c1e3f5b7d2"}\'::jsonb'
    )
    op.execute(
        "DELETE FROM artifact_format_extensions "
        'WHERE provenance = \'{"source":"migration:a9c1e3f5b7d2"}\'::jsonb'
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION phase3_validate_acquisition_artifact()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            prior acquisition_artifacts%ROWTYPE;
            parent acquisition_artifacts%ROWTYPE;
            release_status text;
        BEGIN
            SELECT status INTO STRICT release_status
            FROM artifact_signature_releases
            WHERE id = NEW.signature_release_id
            FOR KEY SHARE;
            IF release_status <> 'active' THEN
                RAISE EXCEPTION
                    'Accepted Artifact requires the active signature release';
            END IF;
            IF NEW.parent_artifact_id IS NOT NULL THEN
                SELECT * INTO STRICT parent
                FROM acquisition_artifacts
                WHERE id = NEW.parent_artifact_id
                FOR KEY SHARE;
                IF parent.id >= NEW.id
                   OR parent.source_endpoint_id <> NEW.source_endpoint_id THEN
                    RAISE EXCEPTION
                        'Artifact parent must be earlier and belong to the same endpoint';
                END IF;
            END IF;
            IF NEW.supersedes_artifact_id IS NOT NULL THEN
                SELECT * INTO STRICT prior
                FROM acquisition_artifacts
                WHERE id = NEW.supersedes_artifact_id
                FOR KEY SHARE;
                IF prior.id >= NEW.id
                   OR prior.source_endpoint_id <> NEW.source_endpoint_id
                   OR prior.resource_identity <> NEW.resource_identity
                   OR prior.parent_artifact_id IS DISTINCT FROM NEW.parent_artifact_id
                   OR prior.member_path IS DISTINCT FROM NEW.member_path
                   OR prior.payload_id = NEW.payload_id THEN
                    RAISE EXCEPTION
                        'Artifact supersession must be forward-only within one '
                        'resource/member scope and use changed accepted bytes';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.drop_index(
        "uq_acquisition_artifacts_root_resource_payload",
        table_name="acquisition_artifacts",
    )
    op.create_unique_constraint(
        "uq_acquisition_artifacts_resource_payload",
        "acquisition_artifacts",
        ["source_endpoint_id", "resource_identity", "payload_id"],
    )
