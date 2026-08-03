"""install Phase 3 corrective catalogs and Artifact Format foundation

Revision ID: c9a2f4e6b801
Revises: b8d4f0a2c315
Create Date: 2026-07-29

This migration corrects endpoint type/method/platform vocabularies without
rewriting referenced historical values, and installs the normalized canonical
Artifact Format and signature-release catalogs. It creates no historical
Artifacts and activates no acquisition runtime.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9a2f4e6b801"
down_revision: str | Sequence[str] | None = "b8d4f0a2c315"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CORRECTIONS_PATH = DATA_DIR / "source_acquisition_catalog_corrections_v1.json"
FORMATS_PATH = DATA_DIR / "artifact_formats_v1.json"
CORRECTION_SEED_SET = "phase3_acquisition_1"
FORMAT_SEED_SET = "phase3_artifact_formats_1"
EXPECTED_CORRECTION_COUNTS = {
    ("endpoint_types", "add"): 5,
    ("endpoint_types", "deactivate"): 1,
    ("acquisition_methods", "add"): 10,
    ("acquisition_methods", "deactivate"): 4,
    ("platforms", "add"): 27,
    ("platforms", "deactivate"): 0,
}
EXPECTED_FORMAT_COUNT = 74
FORMAT_SUPPORT_TABLES = (
    "artifact_format_signatures",
    "artifact_signature_releases",
    "artifact_format_relationships",
    "artifact_format_aliases",
    "artifact_format_extensions",
    "artifact_format_media_types",
    "artifact_format_external_identifiers",
)


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name} must contain one JSON object.")
    return payload


def _load_corrections() -> dict:
    payload = _load_json(CORRECTIONS_PATH)
    if payload.get("seed_set") != CORRECTION_SEED_SET:
        raise RuntimeError("Source acquisition correction seed identity changed.")
    for (catalog, operation), expected in EXPECTED_CORRECTION_COUNTS.items():
        rows = payload.get(catalog, {}).get(operation)
        if not isinstance(rows, list) or len(rows) != expected:
            raise RuntimeError(f"{catalog}.{operation} must contain exactly {expected} values.")
    all_slugs = [
        row["slug"]
        for catalog in ("endpoint_types", "acquisition_methods", "platforms")
        for row in payload[catalog]["add"]
    ]
    if len(all_slugs) != len(set(all_slugs)):
        raise RuntimeError("Corrective catalog additions contain duplicate slugs.")
    return payload


def _load_formats() -> list[dict]:
    payload = _load_json(FORMATS_PATH)
    if payload.get("seed_set") != FORMAT_SEED_SET:
        raise RuntimeError("Artifact Format seed identity changed.")
    rows = payload.get("formats")
    if not isinstance(rows, list) or len(rows) != EXPECTED_FORMAT_COUNT:
        raise RuntimeError(
            f"artifact_formats_v1.json must contain {EXPECTED_FORMAT_COUNT} formats."
        )
    slugs = [row["slug"] for row in rows]
    if len(slugs) != len(set(slugs)):
        raise RuntimeError("Artifact Format seed contains duplicate slugs.")
    slug_set = set(slugs)
    missing_parents = sorted(
        {row["parent"] for row in rows if row.get("parent") and row["parent"] not in slug_set}
    )
    if missing_parents:
        raise RuntimeError(
            "Artifact Format seed references missing parents: " + ", ".join(missing_parents)
        )
    required = {
        "html",
        "plain_text",
        "pdf",
        "json",
        "xml",
        "email_message",
        "ical",
        "jpeg",
        "png",
        "mp4",
        "mp3",
        "flac",
        "webvtt",
        "subrip",
        "zip",
        "tar",
        "gzip",
        "binary",
        "other",
    }
    if not required.issubset(slug_set):
        raise RuntimeError("Artifact Format seed is missing required baseline formats.")
    return rows


def _require_corrective_preflight(corrections: dict) -> None:
    bind = op.get_bind()
    for table_name in ("endpoint_types", "acquisition_methods", "platforms"):
        additions = [row["slug"] for row in corrections[table_name]["add"]]
        collisions = (
            bind.execute(
                sa.text(
                    f"""
                SELECT slug
                FROM {table_name}
                WHERE slug = ANY(CAST(:slugs AS varchar[]))
                ORDER BY slug
                """
                ),
                {"slugs": additions},
            )
            .scalars()
            .all()
        )
        if collisions:
            raise RuntimeError(
                f"Phase 3 cannot seed {table_name}; existing rows collide: " + ", ".join(collisions)
            )

    references = {
        "endpoint_types": ("endpoint_type", corrections["endpoint_types"]["deactivate"]),
        "acquisition_methods": (
            "acquisition_method",
            corrections["acquisition_methods"]["deactivate"],
        ),
    }
    for table_name, (column_name, slugs) in references.items():
        if not slugs:
            continue
        used = bind.execute(
            sa.text(
                f"""
                SELECT {column_name}, count(*)
                FROM source_endpoints
                WHERE {column_name} = ANY(CAST(:slugs AS varchar[]))
                GROUP BY {column_name}
                ORDER BY {column_name}
                """
            ),
            {"slugs": slugs},
        ).all()
        if used:
            details = ", ".join(f"{slug}={count}" for slug, count in used)
            raise RuntimeError(
                "Phase 3 refuses prospective catalog inactivation while "
                f"SourceEndpoints still reference {table_name}: {details}."
            )

    for table_name in ("endpoint_types", "acquisition_methods"):
        targets = corrections[table_name]["deactivate"]
        found = (
            bind.execute(
                sa.text(
                    f"""
                SELECT slug
                FROM {table_name}
                WHERE slug = ANY(CAST(:slugs AS varchar[]))
                  AND is_active
                ORDER BY slug
                """
                ),
                {"slugs": targets},
            )
            .scalars()
            .all()
        )
        if found != sorted(targets):
            raise RuntimeError(
                f"Phase 3 expected active legacy {table_name}: " + ", ".join(sorted(targets))
            )


def _create_format_tables() -> None:
    op.create_table(
        "artifact_formats",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("format_family", sa.String(length=50), nullable=False),
        sa.Column("format_kind", sa.String(length=30), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=True),
        sa.Column("authority_status", sa.String(length=30), nullable=False),
        sa.Column("is_container", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_compression", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_manifest", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "authority_status IN "
            "('registered', 'standardized', 'de_facto', "
            "'vendor_defined', 'local', 'unknown')",
            name=op.f("ck_artifact_formats_authority_status"),
        ),
        sa.CheckConstraint(
            "format_kind IN "
            "('format', 'container', 'compression', 'manifest', "
            "'family', 'fallback')",
            name=op.f("ck_artifact_formats_format_kind"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name=op.f("ck_artifact_formats_valid_interval"),
        ),
        sa.CheckConstraint(
            "(format_kind NOT IN ('family', 'fallback')) OR NOT is_terminal",
            name=op.f("ck_artifact_formats_broad_format_not_terminal"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["artifact_formats.id"],
            name=op.f("fk_artifact_formats_parent_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_formats")),
        sa.UniqueConstraint("slug", name=op.f("uq_artifact_formats_slug")),
    )
    op.create_index(
        "ix_artifact_formats_family_active",
        "artifact_formats",
        ["format_family", "is_active"],
    )
    op.create_index("ix_artifact_formats_parent", "artifact_formats", ["parent_id"])

    op.create_table(
        "artifact_format_external_identifiers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("artifact_format_id", sa.BigInteger(), nullable=False),
        sa.Column("authority_slug", sa.String(length=100), nullable=False),
        sa.Column("scheme", sa.String(length=100), nullable=False),
        sa.Column("external_identifier", sa.String(length=255), nullable=False),
        sa.Column("relation", sa.String(length=40), nullable=False),
        sa.Column("resource_uri", sa.Text(), nullable=True),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relation IN "
            "('exact_match', 'broader_match', 'narrower_match', "
            "'related_match', 'normative_specification', "
            "'preservation_description')",
            name=op.f("ck_artifact_format_external_identifiers_relation"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name=op.f("ck_artifact_format_external_identifiers_valid_interval"),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_format_id"],
            ["artifact_formats.id"],
            name=op.f(
                "fk_artifact_format_external_identifiers_artifact_format_id_artifact_formats"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_format_external_identifiers")),
    )
    op.create_index(
        "ix_artifact_external_identifiers_lookup",
        "artifact_format_external_identifiers",
        ["authority_slug", "scheme", "external_identifier"],
    )
    op.create_index(
        "uq_artifact_external_identifiers_active_mapping",
        "artifact_format_external_identifiers",
        [
            "artifact_format_id",
            "authority_slug",
            "scheme",
            "external_identifier",
            "relation",
        ],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "uq_artifact_external_identifiers_active_exact",
        "artifact_format_external_identifiers",
        ["authority_slug", "scheme", "external_identifier"],
        unique=True,
        postgresql_where=sa.text("is_active AND relation = 'exact_match'"),
    )

    _create_format_evidence_table(
        "artifact_format_media_types",
        "media_type",
        sa.String(length=255),
        "uq_artifact_format_media_types_active_mapping",
        "ix_artifact_format_media_types_lookup",
    )
    _create_format_evidence_table(
        "artifact_format_extensions",
        "extension",
        sa.String(length=50),
        "uq_artifact_format_extensions_active_mapping",
        "ix_artifact_format_extensions_lookup",
        extension_check=True,
    )

    op.create_table(
        "artifact_format_aliases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("artifact_format_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("normalized_alias", sa.String(length=255), nullable=False),
        sa.Column("authority_slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(alias) <> ''",
            name=op.f("ck_artifact_format_aliases_alias_nonempty"),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_format_id"],
            ["artifact_formats.id"],
            name=op.f("fk_artifact_format_aliases_artifact_format_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_format_aliases")),
    )
    op.create_index(
        "ix_artifact_format_aliases_lookup",
        "artifact_format_aliases",
        ["normalized_alias", "is_active"],
    )
    op.create_index(
        "uq_artifact_format_aliases_active_mapping",
        "artifact_format_aliases",
        ["artifact_format_id", "normalized_alias"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "artifact_format_relationships",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("subject_format_id", sa.BigInteger(), nullable=False),
        sa.Column("object_format_id", sa.BigInteger(), nullable=False),
        sa.Column("relation", sa.String(length=30), nullable=False),
        sa.Column("authority_slug", sa.String(length=100), nullable=False),
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relation IN ('exact_match', 'broader_match', 'narrower_match', 'related_match')",
            name=op.f("ck_artifact_format_relationships_relation"),
        ),
        sa.CheckConstraint(
            "subject_format_id <> object_format_id",
            name=op.f("ck_artifact_format_relationships_different_formats"),
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name=op.f("ck_artifact_format_relationships_valid_interval"),
        ),
        sa.ForeignKeyConstraint(
            ["object_format_id"],
            ["artifact_formats.id"],
            name=op.f("fk_artifact_format_relationships_object_format_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_format_id"],
            ["artifact_formats.id"],
            name=op.f("fk_artifact_format_relationships_subject_format_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_format_relationships")),
    )
    op.create_index(
        "ix_artifact_format_relationships_object",
        "artifact_format_relationships",
        ["object_format_id", "relation"],
    )
    op.create_index(
        "uq_artifact_format_relationships_active_mapping",
        "artifact_format_relationships",
        ["subject_format_id", "relation", "object_format_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "artifact_signature_releases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("authority_slug", sa.String(length=100), nullable=False),
        sa.Column("release_identifier", sa.String(length=255), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_length", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_bootstrap", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "authority_signature_verified",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'active', 'rejected', 'retired', 'rolled_back')",
            name=op.f("ck_artifact_signature_releases_status"),
        ),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name=op.f("ck_artifact_signature_releases_sha256"),
        ),
        sa.CheckConstraint(
            "byte_length > 0",
            name=op.f("ck_artifact_signature_releases_byte_length_positive"),
        ),
        sa.CheckConstraint(
            "(status = 'active' AND activated_at IS NOT NULL) OR status <> 'active'",
            name=op.f("ck_artifact_signature_releases_active_has_activation"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_signature_releases")),
        sa.UniqueConstraint(
            "authority_slug",
            "release_identifier",
            name="uq_artifact_signature_releases_authority_identifier",
        ),
        sa.UniqueConstraint("sha256", name="uq_artifact_signature_releases_sha256"),
    )
    op.create_index(
        "uq_artifact_signature_releases_active_authority",
        "artifact_signature_releases",
        ["authority_slug"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "artifact_format_signatures",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("signature_release_id", sa.BigInteger(), nullable=False),
        sa.Column("artifact_format_id", sa.BigInteger(), nullable=False),
        sa.Column("signature_identifier", sa.String(length=255), nullable=False),
        sa.Column("signature_kind", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pattern", postgresql.JSONB(), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "signature_kind IN ('byte_sequence', 'container', 'structural', 'text_marker')",
            name=op.f("ck_artifact_format_signatures_signature_kind"),
        ),
        sa.CheckConstraint(
            "priority >= 0",
            name=op.f("ck_artifact_format_signatures_priority_nonnegative"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(pattern) = 'object'",
            name=op.f("ck_artifact_format_signatures_pattern_object"),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_format_id"],
            ["artifact_formats.id"],
            name=op.f("fk_artifact_format_signatures_artifact_format_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signature_release_id"],
            ["artifact_signature_releases.id"],
            name=op.f(
                "fk_artifact_format_signatures_signature_release_id_artifact_signature_releases"
            ),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_artifact_format_signatures")),
        sa.UniqueConstraint(
            "signature_release_id",
            "artifact_format_id",
            "signature_identifier",
            name="uq_artifact_format_signatures_release_format_identifier",
        ),
    )
    op.create_index(
        "ix_artifact_format_signatures_format_release",
        "artifact_format_signatures",
        ["artifact_format_id", "signature_release_id"],
    )


def _create_format_evidence_table(
    table_name: str,
    value_column: str,
    value_type: sa.types.TypeEngine,
    unique_name: str,
    index_name: str,
    *,
    extension_check: bool = False,
) -> None:
    constraints: list[sa.SchemaItem] = []
    if extension_check:
        constraints.append(
            sa.CheckConstraint(
                "extension = lower(extension) "
                "AND extension !~ '[./\\\\]' "
                "AND btrim(extension) <> ''",
                name=op.f("ck_artifact_format_extensions_normalized_extension"),
            )
        )
    op.create_table(
        table_name,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("artifact_format_id", sa.BigInteger(), nullable=False),
        sa.Column(value_column, value_type, nullable=False),
        sa.Column("authority_slug", sa.String(length=100), nullable=False),
        sa.Column("is_preferred", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "provenance",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        *constraints,
        sa.ForeignKeyConstraint(
            ["artifact_format_id"],
            ["artifact_formats.id"],
            name=op.f(f"fk_{table_name}_artifact_format_id_artifact_formats"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table_name}")),
    )
    op.create_index(index_name, table_name, [value_column, "is_active"])
    op.create_index(
        unique_name,
        table_name,
        ["artifact_format_id", value_column],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def _seed_formats(rows: list[dict]) -> None:
    bind = op.get_bind()
    statement = sa.text(
        """
        INSERT INTO artifact_formats (
            parent_id,
            slug,
            name,
            format_family,
            format_kind,
            authority_status,
            is_container,
            is_compression,
            is_manifest,
            is_terminal,
            provenance,
            metadata
        )
        VALUES (
            CASE
                WHEN CAST(:parent_slug AS varchar) IS NULL THEN NULL
                ELSE (
                    SELECT id FROM artifact_formats WHERE slug = :parent_slug
                )
            END,
            :slug,
            :name,
            :family,
            :kind,
            :authority_status,
            :is_container,
            :is_compression,
            :is_manifest,
            :is_terminal,
            CAST(:provenance AS jsonb),
            CAST(:metadata AS jsonb)
        )
        """
    )
    ordered = [row for row in rows if not row.get("parent")]
    ordered.extend(row for row in rows if row.get("parent"))
    for row in ordered:
        bind.execute(
            statement,
            {
                "parent_slug": row.get("parent"),
                "slug": row["slug"],
                "name": row["name"],
                "family": row["family"],
                "kind": row["kind"],
                "authority_status": row["authority_status"],
                "is_container": bool(row.get("container")),
                "is_compression": bool(row.get("compression")),
                "is_manifest": bool(row.get("manifest")),
                "is_terminal": bool(row["terminal"]),
                "provenance": json.dumps(
                    {
                        "authority_label": row["authority"],
                        "catalog_version": "1.0",
                    }
                ),
                "metadata": json.dumps(
                    {
                        "seed_set": FORMAT_SEED_SET,
                        "catalog_version": "1.0",
                    }
                ),
            },
        )


def _apply_corrective_catalogs(corrections: dict) -> None:
    bind = op.get_bind()
    for table_name in ("endpoint_types", "acquisition_methods", "platforms"):
        for row in corrections[table_name]["add"]:
            bind.execute(
                sa.text(
                    f"""
                    INSERT INTO {table_name} (
                        slug, name, description, is_active, metadata
                    )
                    VALUES (
                        :slug, :name, NULL, true, CAST(:metadata AS jsonb)
                    )
                    """
                ),
                {
                    "slug": row["slug"],
                    "name": row["name"],
                    "metadata": json.dumps(
                        {
                            "seed_set": CORRECTION_SEED_SET,
                            "catalog_version": "1.0",
                        }
                    ),
                },
            )
        deactivated = corrections[table_name]["deactivate"]
        if deactivated:
            bind.execute(
                sa.text(
                    f"""
                    UPDATE {table_name}
                    SET is_active = false,
                        metadata = metadata || CAST(:marker AS jsonb),
                        updated_at = now()
                    WHERE slug = ANY(CAST(:slugs AS varchar[]))
                    """
                ),
                {
                    "slugs": deactivated,
                    "marker": json.dumps(
                        {
                            "phase3_deactivated": True,
                            "phase3_deactivation_reason": "replaced_by_typed_acquisition_contract",
                        }
                    ),
                },
            )


def upgrade() -> None:
    corrections = _load_corrections()
    formats = _load_formats()
    _require_corrective_preflight(corrections)
    _create_format_tables()
    _seed_formats(formats)
    _apply_corrective_catalogs(corrections)


def _require_lossless_downgrade(corrections: dict, formats: list[dict]) -> None:
    bind = op.get_bind()
    populated_support = [
        table_name
        for table_name in FORMAT_SUPPORT_TABLES
        if bind.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name} LIMIT 1)")).scalar_one()
    ]
    if populated_support:
        raise RuntimeError(
            "Refusing Phase 3 catalog downgrade: authority mapping/signature "
            "state exists in " + ", ".join(populated_support) + "."
        )

    expected_by_slug = {row["slug"]: row for row in formats}
    database_rows = (
        bind.execute(
            sa.text(
                """
            SELECT f.slug,
                   f.name,
                   f.format_family,
                   f.format_kind,
                   f.authority_status,
                   f.is_container,
                   f.is_compression,
                   f.is_manifest,
                   f.is_terminal,
                   f.is_active,
                   f.version_label,
                   f.description,
                   f.provenance,
                   f.metadata,
                   parent.slug AS parent_slug
            FROM artifact_formats f
            LEFT JOIN artifact_formats parent ON parent.id = f.parent_id
            ORDER BY f.slug
            """
            )
        )
        .mappings()
        .all()
    )
    if len(database_rows) != len(expected_by_slug):
        raise RuntimeError(
            "Refusing Phase 3 catalog downgrade: custom or missing Artifact "
            "Format rows require forward preservation."
        )
    for database_row in database_rows:
        expected = expected_by_slug.get(database_row["slug"])
        expected_metadata = {
            "seed_set": FORMAT_SEED_SET,
            "catalog_version": "1.0",
        }
        expected_provenance = {
            "authority_label": expected["authority"] if expected else None,
            "catalog_version": "1.0",
        }
        matches = expected is not None and all(
            (
                database_row["name"] == expected["name"],
                database_row["format_family"] == expected["family"],
                database_row["format_kind"] == expected["kind"],
                database_row["authority_status"] == expected["authority_status"],
                database_row["is_container"] == bool(expected.get("container")),
                database_row["is_compression"] == bool(expected.get("compression")),
                database_row["is_manifest"] == bool(expected.get("manifest")),
                database_row["is_terminal"] == bool(expected["terminal"]),
                database_row["is_active"] is True,
                database_row["version_label"] is None,
                database_row["description"] is None,
                database_row["parent_slug"] == expected.get("parent"),
                database_row["provenance"] == expected_provenance,
                database_row["metadata"] == expected_metadata,
            )
        )
        if not matches:
            raise RuntimeError(
                "Refusing Phase 3 catalog downgrade: seeded Artifact Format "
                f"{database_row['slug']!r} changed."
            )

    for table_name in ("endpoint_types", "acquisition_methods", "platforms"):
        expected_additions = {row["slug"]: row["name"] for row in corrections[table_name]["add"]}
        if expected_additions:
            rows = (
                bind.execute(
                    sa.text(
                        f"""
                    SELECT slug, name, description, is_active, metadata
                    FROM {table_name}
                    WHERE slug = ANY(CAST(:slugs AS varchar[]))
                    """
                    ),
                    {"slugs": list(expected_additions)},
                )
                .mappings()
                .all()
            )
            if len(rows) != len(expected_additions):
                raise RuntimeError(
                    f"Refusing Phase 3 downgrade: seeded {table_name} rows are missing."
                )
            for row in rows:
                if (
                    row["name"] != expected_additions[row["slug"]]
                    or row["description"] is not None
                    or row["is_active"] is not True
                    or row["metadata"]
                    != {
                        "seed_set": CORRECTION_SEED_SET,
                        "catalog_version": "1.0",
                    }
                ):
                    raise RuntimeError(
                        f"Refusing Phase 3 downgrade: seeded {table_name} "
                        f"value {row['slug']!r} changed."
                    )

        reference_column = {
            "endpoint_types": "endpoint_type",
            "acquisition_methods": "acquisition_method",
            "platforms": "platform",
        }[table_name]
        referenced = bind.execute(
            sa.text(
                f"""
                SELECT count(*)
                FROM source_endpoints
                WHERE {reference_column} = ANY(CAST(:slugs AS varchar[]))
                """
            ),
            {"slugs": list(expected_additions)},
        ).scalar_one()
        if referenced:
            raise RuntimeError(
                f"Refusing Phase 3 downgrade: {referenced} SourceEndpoint "
                f"row(s) use Phase 3 {table_name} values."
            )

        deactivated = corrections[table_name]["deactivate"]
        if deactivated:
            marker_mismatches = bind.execute(
                sa.text(
                    f"""
                    SELECT count(*)
                    FROM {table_name}
                    WHERE slug = ANY(CAST(:slugs AS varchar[]))
                      AND (
                          is_active
                          OR metadata ->> 'phase3_deactivated' <> 'true'
                          OR metadata ->> 'phase3_deactivation_reason'
                             <> 'replaced_by_typed_acquisition_contract'
                      )
                    """
                ),
                {"slugs": deactivated},
            ).scalar_one()
            if marker_mismatches:
                raise RuntimeError(
                    f"Refusing Phase 3 downgrade: deprecated {table_name} state changed."
                )


def downgrade() -> None:
    corrections = _load_corrections()
    formats = _load_formats()
    _require_lossless_downgrade(corrections, formats)
    bind = op.get_bind()

    for table_name in ("endpoint_types", "acquisition_methods", "platforms"):
        additions = [row["slug"] for row in corrections[table_name]["add"]]
        if additions:
            bind.execute(
                sa.text(
                    f"""
                    DELETE FROM {table_name}
                    WHERE slug = ANY(CAST(:slugs AS varchar[]))
                    """
                ),
                {"slugs": additions},
            )
        deactivated = corrections[table_name]["deactivate"]
        if deactivated:
            bind.execute(
                sa.text(
                    f"""
                    UPDATE {table_name}
                    SET is_active = true,
                        metadata = metadata
                            - 'phase3_deactivated'
                            - 'phase3_deactivation_reason',
                        updated_at = now()
                    WHERE slug = ANY(CAST(:slugs AS varchar[]))
                    """
                ),
                {"slugs": deactivated},
            )

    for table_name in FORMAT_SUPPORT_TABLES:
        op.drop_table(table_name)
    op.drop_index("ix_artifact_formats_parent", table_name="artifact_formats")
    op.drop_index("ix_artifact_formats_family_active", table_name="artifact_formats")
    op.drop_table("artifact_formats")
