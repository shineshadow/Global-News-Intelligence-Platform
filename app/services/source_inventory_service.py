import csv
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.database import async_session_factory
from app.models import Source, SourceEndpoint
from app.repositories import (
    source_endpoint_repository,
    source_repository,
)
from app.services.exceptions import ResourceConflictError


@dataclass(slots=True, frozen=True)
class SourceInventoryImportSummary:
    source_rows: int
    endpoint_rows: int

    sources_created: int
    sources_reused: int

    endpoints_created: int
    endpoints_reused: int


def _normalize_url(url: str) -> str:
    """
    Normalize URLs for duplicate matching.

    This deliberately does not rewrite query strings.
    """

    parts = urlsplit(url.strip())

    path = parts.path or "/"

    if path != "/":
        path = path.rstrip("/")

    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            path,
            parts.query,
            "",
        )
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def _read_metadata(value: str) -> dict:
    if not value:
        return {}

    parsed = json.loads(value)

    if not isinstance(parsed, dict):
        raise ValueError(
            "Inventory metadata_json must contain an object."
        )

    return parsed


def _merge_metadata(
    existing: dict | None,
    incoming: dict,
) -> dict:
    merged = dict(existing or {})
    merged.update(incoming)

    return merged


async def import_source_inventory(
    sources_path: Path,
    endpoints_path: Path,
    *,
    session_factory: async_sessionmaker[
        AsyncSession
    ] = async_session_factory,
) -> SourceInventoryImportSummary:
    """
    Import a versioned source inventory.

    New sources are active.
    New endpoints are deliberately disabled until health checked.

    Re-running this importer is safe: sources and endpoints are
    matched by normalized canonical URLs.
    """

    source_rows = _read_csv(sources_path)
    endpoint_rows = _read_csv(endpoints_path)

    sources_created = 0
    sources_reused = 0
    endpoints_created = 0
    endpoints_reused = 0

    source_key_map: dict[str, Source] = {}

    async with session_factory() as session:
        async with session.begin():
            existing_sources = list(
                (
                    await session.scalars(
                        select(Source)
                    )
                ).all()
            )

            existing_endpoints = list(
                (
                    await session.scalars(
                        select(SourceEndpoint)
                    )
                ).all()
            )

            source_by_url = {
                _normalize_url(source.website_url): source
                for source in existing_sources
                if source.website_url
            }

            endpoint_by_url = {
                _normalize_url(endpoint.url): endpoint
                for endpoint in existing_endpoints
            }

            for row in source_rows:
                source_key = row["source_key"]
                website_url = row["website_url"]

                normalized_url = _normalize_url(
                    website_url
                )

                source = source_by_url.get(
                    normalized_url
                )

                metadata = _read_metadata(
                    row["metadata_json"]
                )

                if source is None:
                    source = (
                        await source_repository.create_source(
                            session,
                            {
                                "name": row["name"],
                                "country": row["country"],
                                "primary_language": (
                                    row["primary_language"]
                                ),
                                "source_type": (
                                    row["source_type"]
                                ),
                                "status": "active",
                                "priority": row["priority"],
                                "website_url": website_url,
                                "source_metadata": metadata,
                            },
                        )
                    )

                    source_by_url[
                        normalized_url
                    ] = source

                    sources_created += 1

                else:
                    sources_reused += 1

                    merged_metadata = _merge_metadata(
                        source.source_metadata,
                        metadata,
                    )

                    await source_repository.update_source(
                        session,
                        source,
                        {
                            "source_metadata": (
                                merged_metadata
                            ),
                        },
                    )

                source_key_map[source_key] = source

            for row in endpoint_rows:
                source_key = row["source_key"]

                source = source_key_map.get(
                    source_key
                )

                if source is None:
                    raise ValueError(
                        f"Unknown source_key: {source_key}"
                    )

                normalized_url = _normalize_url(
                    row["url"]
                )

                endpoint = endpoint_by_url.get(
                    normalized_url
                )

                metadata = _read_metadata(
                    row["metadata_json"]
                )

                if endpoint is None:
                    endpoint = (
                        await source_endpoint_repository
                        .create_source_endpoint(
                            session,
                            {
                                "source_id": source.id,
                                "name": row["name"],
                                "endpoint_type": (
                                    row["endpoint_type"]
                                ),
                                "url": row["url"],
                                # Important:
                                # Celery must not see this endpoint
                                # until verification passes.
                                "status": "disabled",
                                "poll_interval_seconds": int(
                                    row[
                                        "poll_interval_seconds"
                                    ]
                                ),
                                "endpoint_metadata": metadata,
                            },
                        )
                    )

                    endpoint_by_url[
                        normalized_url
                    ] = endpoint

                    endpoints_created += 1

                else:
                    if endpoint.source_id != source.id:
                        raise ResourceConflictError(
                            "Inventory endpoint already "
                            "belongs to another source: "
                            f"{row['url']}"
                        )

                    endpoints_reused += 1

                    merged_metadata = _merge_metadata(
                        endpoint.endpoint_metadata,
                        metadata,
                    )

                    # Deliberately preserve the current status
                    # when an endpoint already exists.
                    await (
                        source_endpoint_repository
                        .update_source_endpoint(
                            session,
                            endpoint,
                            {
                                "endpoint_metadata": (
                                    merged_metadata
                                ),
                            },
                        )
                    )

    return SourceInventoryImportSummary(
        source_rows=len(source_rows),
        endpoint_rows=len(endpoint_rows),
        sources_created=sources_created,
        sources_reused=sources_reused,
        endpoints_created=endpoints_created,
        endpoints_reused=endpoints_reused,
    )