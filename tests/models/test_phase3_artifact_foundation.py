from __future__ import annotations

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.models import (
    AcquisitionArtifact,
    AcquisitionArtifactObservation,
    AcquisitionMethod,
    ArtifactFormat,
    ArtifactFormatExtension,
    ArtifactFormatExternalIdentifier,
    ArtifactFormatMediaType,
    ArtifactPayload,
    ArtifactRejection,
    ArtifactSignatureRelease,
    EndpointType,
    Platform,
)

HASH_A = "a" * 64
HASH_B = "b" * 64
RELEASE_HASH = "c" * 64


async def _endpoint_and_run(session, *, suffix: str = "one") -> tuple[int, int, int]:
    source_id = int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO sources (
                        name, country, primary_language, source_type
                    )
                    VALUES (
                        :name, 'Testland', 'en', 'news_organization'
                    )
                    RETURNING id
                    """
                ),
                {"name": f"Artifact Source {suffix}"},
            )
        ).scalar_one()
    )
    endpoint_id = int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO source_endpoints (
                        source_id, endpoint_type, endpoint_format,
                        acquisition_method, url
                    )
                    VALUES (
                        :source_id, 'feed', 'rss', 'feed_parser', :url
                    )
                    RETURNING id
                    """
                ),
                {
                    "source_id": source_id,
                    "url": f"https://example.test/{suffix}.xml",
                },
            )
        ).scalar_one()
    )
    run_id = int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO ingestion_runs (
                        source_id, source_endpoint_id, endpoint_url
                    )
                    VALUES (:source_id, :endpoint_id, :url)
                    RETURNING id
                    """
                ),
                {
                    "source_id": source_id,
                    "endpoint_id": endpoint_id,
                    "url": f"https://example.test/{suffix}.xml",
                },
            )
        ).scalar_one()
    )
    return source_id, endpoint_id, run_id


async def _second_run(session, *, source_id: int, endpoint_id: int) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO ingestion_runs (
                        source_id, source_endpoint_id, endpoint_url
                    )
                    VALUES (
                        :source_id, :endpoint_id,
                        'https://example.test/second.xml'
                    )
                    RETURNING id
                    """
                ),
                {"source_id": source_id, "endpoint_id": endpoint_id},
            )
        ).scalar_one()
    )


async def _active_release(session) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO artifact_signature_releases (
                        authority_slug, release_identifier, source_uri,
                        sha256, byte_length, status, is_bootstrap,
                        activated_at
                    )
                    VALUES (
                        'test_authority', 'test-release-1',
                        'https://example.test/signatures',
                        :sha256, 100, 'active', true, now()
                    )
                    RETURNING id
                    """
                ),
                {"sha256": RELEASE_HASH},
            )
        ).scalar_one()
    )


async def _payload(
    session,
    *,
    content_hash: str,
    storage_reference: str,
    format_slug: str = "json",
) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO artifact_payloads (
                        content_hash, byte_length, storage_backend,
                        storage_reference, artifact_format_id
                    )
                    SELECT
                        :content_hash, 100, 'filesystem',
                        :storage_reference, id
                    FROM artifact_formats
                    WHERE slug = :format_slug
                    RETURNING id
                    """
                ),
                {
                    "content_hash": content_hash,
                    "storage_reference": storage_reference,
                    "format_slug": format_slug,
                },
            )
        ).scalar_one()
    )


async def _artifact(
    session,
    *,
    endpoint_id: int,
    payload_id: int,
    release_id: int,
    supersedes_artifact_id: int | None = None,
) -> int:
    return int(
        (
            await session.execute(
                text(
                    """
                    INSERT INTO acquisition_artifacts (
                        source_endpoint_id, payload_id,
                        supersedes_artifact_id, resource_identity,
                        adapter_slug, adapter_version,
                        configuration_version, signature_release_id,
                        detector_name, detector_version,
                        scanner_name, scanner_version,
                        scanner_signature_version,
                        safe_parser_name, safe_parser_version,
                        detection_confidence,
                        identification_evidence,
                        retrieval_provenance
                    )
                    VALUES (
                        :endpoint_id, :payload_id,
                        :supersedes_artifact_id, 'provider:item-1',
                        'test_adapter', '1', '1', :release_id,
                        'test_detector', '1',
                        'test_scanner', '1', 'test-signatures-1',
                        'test_parser', '1', 1.0,
                        '{"signature": "matched"}'::jsonb,
                        '{"test": true}'::jsonb
                    )
                    RETURNING id
                    """
                ),
                {
                    "endpoint_id": endpoint_id,
                    "payload_id": payload_id,
                    "release_id": release_id,
                    "supersedes_artifact_id": supersedes_artifact_id,
                },
            )
        ).scalar_one()
    )


async def _observation(
    session,
    *,
    artifact_id: int,
    run_id: int,
    retrieval_identity: str,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO acquisition_artifact_observations (
                artifact_id, ingestion_run_id, retrieval_identity,
                original_locator, original_filename,
                declared_media_type, observed_media_type,
                extension_chain, retrieval_evidence
            )
            VALUES (
                :artifact_id, :run_id, :retrieval_identity,
                'https://example.test/item.json', 'item.json',
                'application/json', 'application/json',
                '["json"]'::jsonb, '{"status": 200}'::jsonb
            )
            """
        ),
        {
            "artifact_id": artifact_id,
            "run_id": run_id,
            "retrieval_identity": retrieval_identity,
        },
    )


async def test_corrective_source_acquisition_catalogs_are_seeded(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        endpoint_types = dict(
            (
                await session.execute(
                    select(EndpointType.slug, EndpointType.is_active).where(
                        EndpointType.slug.in_(
                            {
                                "audio_platform",
                                "messaging_platform",
                                "object_storage",
                                "cloud_storage",
                                "message_queue",
                                "podcast",
                            }
                        )
                    )
                )
            ).all()
        )
        methods = dict(
            (
                await session.execute(
                    select(AcquisitionMethod.slug, AcquisitionMethod.is_active).where(
                        AcquisitionMethod.slug.in_(
                            {
                                "email_client",
                                "file_transfer",
                                "storage_client",
                                "repository_sync",
                                "media_downloader",
                                "imap",
                                "pop3",
                                "ftp",
                                "sftp",
                            }
                        )
                    )
                )
            ).all()
        )
        added_platform_count = await session.scalar(
            select(func.count(Platform.id)).where(
                Platform.metadata_json["seed_set"].astext == "phase3_acquisition_1"
            )
        )

    assert endpoint_types == {
        "audio_platform": True,
        "messaging_platform": True,
        "object_storage": True,
        "cloud_storage": True,
        "message_queue": True,
        "podcast": False,
    }
    assert methods == {
        "email_client": True,
        "file_transfer": True,
        "storage_client": True,
        "repository_sync": True,
        "media_downloader": True,
        "imap": False,
        "pop3": False,
        "ftp": False,
        "sftp": False,
    }
    assert added_platform_count == 27


async def test_artifact_format_catalog_is_canonical_and_broad_values_are_nonterminal(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        formats = {
            row.slug: row
            for row in (
                await session.execute(
                    select(
                        ArtifactFormat.slug,
                        ArtifactFormat.authority_status,
                        ArtifactFormat.is_terminal,
                    ).where(
                        ArtifactFormat.slug.in_(
                            {
                                "json",
                                "pdf",
                                "jpeg",
                                "mp4",
                                "flac",
                                "webvtt",
                                "zip",
                                "image",
                                "audio",
                                "video",
                                "archive",
                                "binary",
                                "other",
                            }
                        )
                    )
                )
            ).all()
        }
        seeded_count = await session.scalar(
            select(func.count(ArtifactFormat.id)).where(
                ArtifactFormat.format_metadata["seed_set"].astext == "phase3_artifact_formats_1"
            )
        )
        evidence_counts = {
            "external": await session.scalar(
                select(func.count(ArtifactFormatExternalIdentifier.id))
            ),
            "media": await session.scalar(select(func.count(ArtifactFormatMediaType.id))),
            "extension": await session.scalar(select(func.count(ArtifactFormatExtension.id))),
        }

    assert seeded_count == 74
    assert all(
        formats[slug].authority_status
        in {"registered", "standardized", "de_facto", "vendor_defined"}
        for slug in ("json", "pdf", "jpeg", "mp4", "flac", "webvtt", "zip")
    )
    assert all(
        formats[slug].is_terminal
        for slug in ("json", "pdf", "jpeg", "mp4", "flac", "webvtt", "zip")
    )
    assert all(
        not formats[slug].is_terminal
        for slug in ("image", "audio", "video", "archive", "binary", "other")
    )
    assert evidence_counts == {"external": 0, "media": 12, "extension": 9}


async def test_external_mapping_history_accumulates_but_active_exact_identity_is_unique(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        json_id = int(
            await session.scalar(select(ArtifactFormat.id).where(ArtifactFormat.slug == "json"))
        )
        pdf_id = int(
            await session.scalar(select(ArtifactFormat.id).where(ArtifactFormat.slug == "pdf"))
        )
        await session.execute(
            text(
                """
                INSERT INTO artifact_format_external_identifiers (
                    artifact_format_id, authority_slug, scheme,
                    external_identifier, relation, is_active
                )
                VALUES
                    (:json_id, 'test', 'test_scheme', 'format-1',
                     'exact_match', false),
                    (:json_id, 'test', 'test_scheme', 'format-1',
                     'exact_match', false),
                    (:json_id, 'test', 'test_scheme', 'format-1',
                     'exact_match', true),
                    (:pdf_id, 'test', 'test_scheme', 'format-1',
                     'related_match', true)
                """
            ),
            {"json_id": json_id, "pdf_id": pdf_id},
        )

    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(ArtifactFormatExternalIdentifier.id))) == 4

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO artifact_format_external_identifiers (
                            artifact_format_id, authority_slug, scheme,
                            external_identifier, relation, is_active
                        )
                        VALUES (
                            :pdf_id, 'test', 'test_scheme', 'format-1',
                            'exact_match', true
                        )
                        """
                    ),
                    {"pdf_id": pdf_id},
                )


def test_artifact_models_separate_payload_version_observation_and_rejection() -> None:
    assert "storage_reference" in ArtifactPayload.__table__.columns
    assert "storage_reference" not in ArtifactRejection.__table__.columns
    assert "ingestion_run_id" not in AcquisitionArtifact.__table__.columns
    assert "ingestion_run_id" in AcquisitionArtifactObservation.__table__.columns
    assert AcquisitionArtifact.__table__.c.supersedes_artifact_id.nullable is True
    assert ArtifactRejection.__table__.c.deleted_at.nullable is False
    assert ArtifactRejection.__table__.c.deletion_verified.nullable is False


async def test_broad_artifact_format_cannot_back_an_accepted_payload(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="active terminal Artifact Format"):
            async with session.begin():
                await _payload(
                    session,
                    content_hash=HASH_A,
                    storage_reference="accepted/broad",
                    format_slug="image",
                )


async def test_duplicate_reacquisition_preserves_observation_without_duplicate_bytes(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        source_id, endpoint_id, first_run_id = await _endpoint_and_run(session)
        second_run_id = await _second_run(session, source_id=source_id, endpoint_id=endpoint_id)
        release_id = await _active_release(session)
        payload_id = await _payload(
            session,
            content_hash=HASH_A,
            storage_reference="accepted/a",
        )
        artifact_id = await _artifact(
            session,
            endpoint_id=endpoint_id,
            payload_id=payload_id,
            release_id=release_id,
        )
        await _observation(
            session,
            artifact_id=artifact_id,
            run_id=first_run_id,
            retrieval_identity="scheduled:one:item-1",
        )
        await _observation(
            session,
            artifact_id=artifact_id,
            run_id=second_run_id,
            retrieval_identity="scheduled:two:item-1",
        )

    async with database_session_factory() as session:
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 1
        assert await session.scalar(select(func.count(AcquisitionArtifact.id))) == 1
        assert await session.scalar(select(func.count(AcquisitionArtifactObservation.id))) == 2


async def test_changed_bytes_append_forward_immutable_artifact_version(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        _, endpoint_id, _ = await _endpoint_and_run(session)
        release_id = await _active_release(session)
        first_payload_id = await _payload(
            session,
            content_hash=HASH_A,
            storage_reference="accepted/a",
        )
        first_artifact_id = await _artifact(
            session,
            endpoint_id=endpoint_id,
            payload_id=first_payload_id,
            release_id=release_id,
        )
        second_payload_id = await _payload(
            session,
            content_hash=HASH_B,
            storage_reference="accepted/b",
        )
        second_artifact_id = await _artifact(
            session,
            endpoint_id=endpoint_id,
            payload_id=second_payload_id,
            release_id=release_id,
            supersedes_artifact_id=first_artifact_id,
        )

    async with database_session_factory() as session:
        successor = await session.get(AcquisitionArtifact, second_artifact_id)
        assert successor is not None
        assert successor.supersedes_artifact_id == first_artifact_id
        assert await session.scalar(select(func.count(ArtifactPayload.id))) == 2
        assert await session.scalar(select(func.count(AcquisitionArtifact.id))) == 2

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="append-only and immutable"):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE acquisition_artifacts
                        SET resource_identity = 'changed'
                        WHERE id = :artifact_id
                        """
                    ),
                    {"artifact_id": first_artifact_id},
                )


async def test_artifact_supersession_rejects_cross_resource_history(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        _, endpoint_id, _ = await _endpoint_and_run(session)
        release_id = await _active_release(session)
        first_payload_id = await _payload(
            session,
            content_hash=HASH_A,
            storage_reference="accepted/a",
        )
        first_artifact_id = await _artifact(
            session,
            endpoint_id=endpoint_id,
            payload_id=first_payload_id,
            release_id=release_id,
        )
        second_payload_id = await _payload(
            session,
            content_hash=HASH_B,
            storage_reference="accepted/b",
        )

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="forward-only"):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO acquisition_artifacts (
                            source_endpoint_id, payload_id,
                            supersedes_artifact_id, resource_identity,
                            adapter_slug, adapter_version,
                            configuration_version, signature_release_id,
                            detector_name, detector_version,
                            scanner_name, scanner_version,
                            scanner_signature_version,
                            safe_parser_name, safe_parser_version,
                            detection_confidence
                        )
                        VALUES (
                            :endpoint_id, :payload_id, :prior_id,
                            'provider:different-item',
                            'test_adapter', '1', '1', :release_id,
                            'test_detector', '1',
                            'test_scanner', '1', 'test-signatures-1',
                            'test_parser', '1', 1.0
                        )
                        """
                    ),
                    {
                        "endpoint_id": endpoint_id,
                        "payload_id": second_payload_id,
                        "prior_id": first_artifact_id,
                        "release_id": release_id,
                    },
                )


async def test_rejection_requires_verified_prior_deletion_and_is_immutable(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        _, endpoint_id, run_id = await _endpoint_and_run(session)

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO artifact_rejections (
                            source_endpoint_id, ingestion_run_id,
                            retrieval_identity, content_hash, byte_length,
                            reason_code, rejection_reason,
                            deletion_verified, deleted_at
                        )
                        VALUES (
                            :endpoint_id, :run_id, 'rejected:item-1',
                            :content_hash, 100, 'signature_mismatch',
                            'Signature and extension conflict',
                            false, now()
                        )
                        """
                    ),
                    {
                        "endpoint_id": endpoint_id,
                        "run_id": run_id,
                        "content_hash": HASH_A,
                    },
                )

    async with database_session_factory() as session, session.begin():
        rejection_id = int(
            (
                await session.execute(
                    text(
                        """
                        INSERT INTO artifact_rejections (
                            source_endpoint_id, ingestion_run_id,
                            retrieval_identity, content_hash, byte_length,
                            reason_code, rejection_reason,
                            deletion_verified, deleted_at
                        )
                        VALUES (
                            :endpoint_id, :run_id, 'rejected:item-1',
                            :content_hash, 100, 'signature_mismatch',
                            'Signature and extension conflict',
                            true, now()
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "endpoint_id": endpoint_id,
                        "run_id": run_id,
                        "content_hash": HASH_A,
                    },
                )
            ).scalar_one()
        )

    async with database_session_factory() as session:
        with pytest.raises(DBAPIError, match="append-only and immutable"):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        UPDATE artifact_rejections
                        SET rejection_reason = 'changed'
                        WHERE id = :rejection_id
                        """
                    ),
                    {"rejection_id": rejection_id},
                )


async def test_artifact_acceptance_rejects_invalid_confidence(
    database_session_factory,
) -> None:
    async with database_session_factory() as session, session.begin():
        _, endpoint_id, _ = await _endpoint_and_run(session)
        release_id = await _active_release(session)
        payload_id = await _payload(
            session,
            content_hash=HASH_A,
            storage_reference="accepted/a",
        )

    async with database_session_factory() as session:
        with pytest.raises(IntegrityError):
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO acquisition_artifacts (
                            source_endpoint_id, payload_id, resource_identity,
                            adapter_slug, adapter_version,
                            configuration_version, signature_release_id,
                            detector_name, detector_version,
                            scanner_name, scanner_version,
                            scanner_signature_version,
                            safe_parser_name, safe_parser_version,
                            detection_confidence
                        )
                        VALUES (
                            :endpoint_id, :payload_id, 'provider:item-1',
                            'test_adapter', '1', '1', :release_id,
                            'test_detector', '1',
                            'test_scanner', '1', 'test-signatures-1',
                            'test_parser', '1', 1.1
                        )
                        """
                    ),
                    {
                        "endpoint_id": endpoint_id,
                        "payload_id": payload_id,
                        "release_id": release_id,
                    },
                )


async def test_no_historical_artifact_rows_are_fabricated(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        counts = {
            "payloads": await session.scalar(select(func.count(ArtifactPayload.id))),
            "artifacts": await session.scalar(select(func.count(AcquisitionArtifact.id))),
            "observations": await session.scalar(
                select(func.count(AcquisitionArtifactObservation.id))
            ),
            "rejections": await session.scalar(select(func.count(ArtifactRejection.id))),
            "signature_releases": await session.scalar(
                select(func.count(ArtifactSignatureRelease.id))
            ),
        }

    assert counts == {
        "payloads": 0,
        "artifacts": 0,
        "observations": 0,
        "rejections": 0,
        "signature_releases": 0,
    }
