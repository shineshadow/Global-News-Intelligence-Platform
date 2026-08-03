"""install immutable Phase 3 Artifact persistence foundation

Revision ID: d1b3e5f7a902
Revises: c9a2f4e6b801
Create Date: 2026-07-29

Create content-addressed accepted payloads, immutable endpoint-resource
Artifact versions, append-only reacquisition observations, and post-deletion
rejection metadata. Existing Documents are deliberately not backfilled.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1b3e5f7a902"
down_revision: str | Sequence[str] | None = "c9a2f4e6b801"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ARTIFACT_TABLES = (
    "artifact_rejections",
    "acquisition_artifact_observations",
    "acquisition_artifacts",
    "artifact_payloads",
)


def _create_payloads() -> None:
    op.create_table(
        "artifact_payloads",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "hash_algorithm",
            sa.String(length=20),
            server_default="sha256",
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("storage_backend", sa.String(length=30), nullable=False),
        sa.Column("storage_reference", sa.Text(), nullable=False),
        sa.Column("artifact_format_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "hash_algorithm = 'sha256'",
            name=op.f("ck_artifact_payloads_hash_algorithm"),
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_payloads_content_hash"),
        ),
        sa.CheckConstraint(
            "byte_length > 0",
            name=op.f("ck_artifact_payloads_byte_length_positive"),
        ),
        sa.CheckConstraint(
            "storage_backend IN ('filesystem', 'object_storage')",
            name=op.f("ck_artifact_payloads_storage_backend"),
        ),
        sa.CheckConstraint(
            "btrim(storage_reference) <> ''",
            name=op.f("ck_artifact_payloads_storage_reference_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_format_id"],
            ["artifact_formats.id"],
            name=op.f("fk_artifact_payloads_artifact_format_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_payloads")),
        sa.UniqueConstraint(
            "hash_algorithm",
            "content_hash",
            "byte_length",
            name="uq_artifact_payloads_content_identity",
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_artifact_payloads_public_id")),
        sa.UniqueConstraint(
            "storage_backend",
            "storage_reference",
            name="uq_artifact_payloads_storage_reference",
        ),
    )
    op.create_index(
        "ix_artifact_payloads_format_created",
        "artifact_payloads",
        ["artifact_format_id", "created_at"],
    )


def _create_artifacts() -> None:
    op.create_table(
        "acquisition_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_endpoint_id", sa.BigInteger(), nullable=False),
        sa.Column("payload_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_artifact_id", sa.BigInteger(), nullable=True),
        sa.Column("supersedes_artifact_id", sa.BigInteger(), nullable=True),
        sa.Column("resource_identity", sa.Text(), nullable=False),
        sa.Column("member_path", sa.Text(), nullable=True),
        sa.Column("adapter_slug", sa.String(length=100), nullable=False),
        sa.Column("adapter_version", sa.String(length=100), nullable=False),
        sa.Column("configuration_version", sa.String(length=100), nullable=False),
        sa.Column("signature_release_id", sa.BigInteger(), nullable=False),
        sa.Column("detector_name", sa.String(length=100), nullable=False),
        sa.Column("detector_version", sa.String(length=100), nullable=False),
        sa.Column("scanner_name", sa.String(length=100), nullable=False),
        sa.Column("scanner_version", sa.String(length=100), nullable=False),
        sa.Column("scanner_signature_version", sa.String(length=255), nullable=False),
        sa.Column("safe_parser_name", sa.String(length=100), nullable=False),
        sa.Column("safe_parser_version", sa.String(length=100), nullable=False),
        sa.Column("detection_confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column(
            "identification_evidence",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "retrieval_provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(resource_identity) <> ''",
            name=op.f("ck_acquisition_artifacts_resource_identity_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(adapter_slug) <> ''",
            name=op.f("ck_acquisition_artifacts_adapter_slug_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(adapter_version) <> ''",
            name=op.f("ck_acquisition_artifacts_adapter_version_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(configuration_version) <> ''",
            name=op.f("ck_acquisition_artifacts_configuration_version_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(detector_name) <> '' AND btrim(detector_version) <> ''",
            name=op.f("ck_acquisition_artifacts_detector_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(scanner_name) <> '' "
            "AND btrim(scanner_version) <> '' "
            "AND btrim(scanner_signature_version) <> ''",
            name=op.f("ck_acquisition_artifacts_scanner_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(safe_parser_name) <> '' AND btrim(safe_parser_version) <> ''",
            name=op.f("ck_acquisition_artifacts_safe_parser_nonempty"),
        ),
        sa.CheckConstraint(
            "detection_confidence >= 0 AND detection_confidence <= 1",
            name=op.f("ck_acquisition_artifacts_detection_confidence"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(identification_evidence) = 'object'",
            name=op.f("ck_acquisition_artifacts_identification_evidence_object"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(retrieval_provenance) = 'object'",
            name=op.f("ck_acquisition_artifacts_retrieval_provenance_object"),
        ),
        sa.CheckConstraint(
            "(parent_artifact_id IS NULL AND member_path IS NULL) OR "
            "(parent_artifact_id IS NOT NULL "
            "AND member_path IS NOT NULL "
            "AND btrim(member_path) <> '' "
            "AND member_path !~ '(^/|(^|/)\\.\\.(/|$))')",
            name=op.f("ck_acquisition_artifacts_member_scope"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_artifact_id"],
            ["acquisition_artifacts.id"],
            name=op.f("fk_acquisition_artifacts_parent_artifact_id_acquisition_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payload_id"],
            ["artifact_payloads.id"],
            name=op.f("fk_acquisition_artifacts_payload_id_artifact_payloads"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signature_release_id"],
            ["artifact_signature_releases.id"],
            name=op.f("fk_acquisition_artifacts_signature_release_id_artifact_signature_releases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_endpoint_id"],
            ["source_endpoints.id"],
            name=op.f("fk_acquisition_artifacts_source_endpoint_id_source_endpoints"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_artifact_id"],
            ["acquisition_artifacts.id"],
            name=op.f("fk_acquisition_artifacts_supersedes_artifact_id_acquisition_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acquisition_artifacts")),
        sa.UniqueConstraint(
            "parent_artifact_id",
            "member_path",
            name="uq_acquisition_artifacts_parent_member",
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_acquisition_artifacts_public_id")),
        sa.UniqueConstraint(
            "source_endpoint_id",
            "resource_identity",
            "payload_id",
            name="uq_acquisition_artifacts_resource_payload",
        ),
    )
    op.create_index(
        "ix_acquisition_artifacts_endpoint_accepted",
        "acquisition_artifacts",
        ["source_endpoint_id", "accepted_at"],
    )
    op.create_index(
        "uq_acquisition_artifacts_supersedes",
        "acquisition_artifacts",
        ["supersedes_artifact_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_artifact_id IS NOT NULL"),
    )


def _create_observations() -> None:
    op.create_table(
        "acquisition_artifact_observations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("artifact_id", sa.BigInteger(), nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=False),
        sa.Column("retrieval_identity", sa.Text(), nullable=False),
        sa.Column("original_locator", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("declared_media_type", sa.String(length=255), nullable=True),
        sa.Column("observed_media_type", sa.String(length=255), nullable=True),
        sa.Column(
            "extension_chain",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "retrieval_evidence",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(retrieval_identity) <> ''",
            name=op.f("ck_acquisition_artifact_observations_retrieval_identity_nonempty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(extension_chain) = 'array'",
            name=op.f("ck_acquisition_artifact_observations_extension_chain_array"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(retrieval_evidence) = 'object'",
            name=op.f("ck_acquisition_artifact_observations_retrieval_evidence_object"),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["acquisition_artifacts.id"],
            name=op.f("fk_acquisition_artifact_observations_artifact_id_acquisition_artifacts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_acquisition_artifact_observations_ingestion_run_id_ingestion_runs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acquisition_artifact_observations")),
        sa.UniqueConstraint(
            "ingestion_run_id",
            "retrieval_identity",
            name="uq_acquisition_artifact_observations_run_identity",
        ),
    )
    op.create_index(
        "ix_acquisition_artifact_observations_artifact_observed",
        "acquisition_artifact_observations",
        ["artifact_id", "observed_at"],
    )


def _create_rejections() -> None:
    op.create_table(
        "artifact_rejections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_endpoint_id", sa.BigInteger(), nullable=False),
        sa.Column("ingestion_run_id", sa.BigInteger(), nullable=False),
        sa.Column("retrieval_identity", sa.Text(), nullable=False),
        sa.Column("detected_format_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "hash_algorithm",
            sa.String(length=20),
            server_default="sha256",
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
        sa.Column("detector_name", sa.String(length=100), nullable=True),
        sa.Column("detector_version", sa.String(length=100), nullable=True),
        sa.Column("signature_release_id", sa.BigInteger(), nullable=True),
        sa.Column("scanner_name", sa.String(length=100), nullable=True),
        sa.Column("scanner_version", sa.String(length=100), nullable=True),
        sa.Column(
            "declared_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "detected_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "deletion_verified",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "hash_algorithm = 'sha256'",
            name=op.f("ck_artifact_rejections_hash_algorithm"),
        ),
        sa.CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_rejections_content_hash"),
        ),
        sa.CheckConstraint(
            "byte_length >= 0",
            name=op.f("ck_artifact_rejections_byte_length_nonnegative"),
        ),
        sa.CheckConstraint(
            "deletion_verified",
            name=op.f("ck_artifact_rejections_deletion_verified"),
        ),
        sa.CheckConstraint(
            "deleted_at <= recorded_at",
            name=op.f("ck_artifact_rejections_deleted_before_recorded"),
        ),
        sa.CheckConstraint(
            "btrim(retrieval_identity) <> ''",
            name=op.f("ck_artifact_rejections_retrieval_identity_nonempty"),
        ),
        sa.CheckConstraint(
            "btrim(reason_code) <> '' AND btrim(rejection_reason) <> ''",
            name=op.f("ck_artifact_rejections_rejection_reason_nonempty"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(declared_metadata) = 'object' "
            "AND jsonb_typeof(detected_metadata) = 'object' "
            "AND jsonb_typeof(provenance) = 'object'",
            name=op.f("ck_artifact_rejections_metadata_objects"),
        ),
        sa.ForeignKeyConstraint(
            ["detected_format_id"],
            ["artifact_formats.id"],
            name=op.f("fk_artifact_rejections_detected_format_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_artifact_rejections_ingestion_run_id_ingestion_runs"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signature_release_id"],
            ["artifact_signature_releases.id"],
            name=op.f("fk_artifact_rejections_signature_release_id_artifact_signature_releases"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_endpoint_id"],
            ["source_endpoints.id"],
            name=op.f("fk_artifact_rejections_source_endpoint_id_source_endpoints"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_rejections")),
        sa.UniqueConstraint("public_id", name=op.f("uq_artifact_rejections_public_id")),
        sa.UniqueConstraint(
            "ingestion_run_id",
            "retrieval_identity",
            name="uq_artifact_rejections_run_identity",
        ),
    )
    op.create_index(
        "ix_artifact_rejections_endpoint_recorded",
        "artifact_rejections",
        ["source_endpoint_id", "recorded_at"],
    )
    op.create_index(
        "ix_artifact_rejections_reason_recorded",
        "artifact_rejections",
        ["reason_code", "recorded_at"],
    )


def _create_validation_triggers() -> None:
    op.execute(
        """
        CREATE FUNCTION phase3_artifact_reject_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only and immutable', TG_TABLE_NAME;
        END;
        $$;

        CREATE TRIGGER trg_artifact_payloads_immutable
        BEFORE UPDATE OR DELETE ON artifact_payloads
        FOR EACH ROW EXECUTE FUNCTION phase3_artifact_reject_mutation();

        CREATE TRIGGER trg_acquisition_artifacts_immutable
        BEFORE UPDATE OR DELETE ON acquisition_artifacts
        FOR EACH ROW EXECUTE FUNCTION phase3_artifact_reject_mutation();

        CREATE TRIGGER trg_acquisition_artifact_observations_immutable
        BEFORE UPDATE OR DELETE ON acquisition_artifact_observations
        FOR EACH ROW EXECUTE FUNCTION phase3_artifact_reject_mutation();

        CREATE TRIGGER trg_artifact_rejections_immutable
        BEFORE UPDATE OR DELETE ON artifact_rejections
        FOR EACH ROW EXECUTE FUNCTION phase3_artifact_reject_mutation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase3_validate_artifact_payload()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE format_row artifact_formats%ROWTYPE;
        BEGIN
            SELECT * INTO STRICT format_row
            FROM artifact_formats
            WHERE id = NEW.artifact_format_id
            FOR KEY SHARE;

            IF NOT format_row.is_active OR NOT format_row.is_terminal THEN
                RAISE EXCEPTION
                    'Accepted payload requires one active terminal Artifact Format';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_artifact_payload_format
        BEFORE INSERT ON artifact_payloads
        FOR EACH ROW EXECUTE FUNCTION phase3_validate_artifact_payload();
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase3_validate_acquisition_artifact()
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
                   OR prior.parent_artifact_id
                      IS DISTINCT FROM NEW.parent_artifact_id
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

        CREATE TRIGGER trg_acquisition_artifact_scope
        BEFORE INSERT ON acquisition_artifacts
        FOR EACH ROW EXECUTE FUNCTION phase3_validate_acquisition_artifact();
        """
    )
    op.execute(
        """
        CREATE FUNCTION phase3_validate_artifact_observation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            artifact_endpoint_id bigint;
            run_endpoint_id bigint;
        BEGIN
            SELECT source_endpoint_id INTO STRICT artifact_endpoint_id
            FROM acquisition_artifacts
            WHERE id = NEW.artifact_id
            FOR KEY SHARE;
            SELECT source_endpoint_id INTO STRICT run_endpoint_id
            FROM ingestion_runs
            WHERE id = NEW.ingestion_run_id
            FOR KEY SHARE;
            IF run_endpoint_id IS NULL
               OR run_endpoint_id <> artifact_endpoint_id
            THEN
                RAISE EXCEPTION
                    'Artifact observation run and Artifact must share one endpoint';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_artifact_observation_scope
        BEFORE INSERT ON acquisition_artifact_observations
        FOR EACH ROW EXECUTE FUNCTION phase3_validate_artifact_observation();

        CREATE FUNCTION phase3_validate_artifact_rejection()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE run_endpoint_id bigint;
        BEGIN
            SELECT source_endpoint_id INTO STRICT run_endpoint_id
            FROM ingestion_runs
            WHERE id = NEW.ingestion_run_id
            FOR KEY SHARE;
            IF run_endpoint_id IS NULL
               OR run_endpoint_id <> NEW.source_endpoint_id
            THEN
                RAISE EXCEPTION
                    'Artifact rejection run and rejection must share one endpoint';
            END IF;
            RETURN NEW;
        END;
        $$;

        CREATE TRIGGER trg_artifact_rejection_scope
        BEFORE INSERT ON artifact_rejections
        FOR EACH ROW EXECUTE FUNCTION phase3_validate_artifact_rejection();
        """
    )


def upgrade() -> None:
    _create_payloads()
    _create_artifacts()
    _create_observations()
    _create_rejections()
    _create_validation_triggers()


def downgrade() -> None:
    bind = op.get_bind()
    populated = [
        table_name
        for table_name in ARTIFACT_TABLES
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)")).scalar_one()
    ]
    if populated:
        raise RuntimeError(
            "Refusing Phase 3 Artifact downgrade: accepted/rejected Artifact "
            "state exists in " + ", ".join(populated) + "."
        )

    op.drop_table("artifact_rejections")
    op.drop_table("acquisition_artifact_observations")
    op.drop_table("acquisition_artifacts")
    op.drop_table("artifact_payloads")
    op.execute(
        """
        DROP FUNCTION phase3_validate_artifact_rejection();
        DROP FUNCTION phase3_validate_artifact_observation();
        DROP FUNCTION phase3_validate_acquisition_artifact();
        DROP FUNCTION phase3_validate_artifact_payload();
        DROP FUNCTION phase3_artifact_reject_mutation();
        """
    )
