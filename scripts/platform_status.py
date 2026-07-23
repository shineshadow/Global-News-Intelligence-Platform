import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.database import (
    async_session_factory,
    engine,
)
from app.models import (
    Document,
    IngestionRun,
    Source,
    SourceEndpoint,
)
from app.redis_client import redis_client


async def main() -> None:
    try:
        now = datetime.now(UTC)
        since_24h = now - timedelta(hours=24)
        since_7d = now - timedelta(days=7)

        redis_ok = False

        try:
            redis_ok = bool(
                await redis_client.ping()
            )
        except Exception:
            pass

        async with async_session_factory() as session:
            active_sources = int(
                await session.scalar(
                    select(
                        func.count(Source.id)
                    ).where(
                        Source.status == "active"
                    )
                )
                or 0
            )

            active_endpoints = int(
                await session.scalar(
                    select(
                        func.count(
                            SourceEndpoint.id
                        )
                    ).where(
                        SourceEndpoint.status
                        == "active"
                    )
                )
                or 0
            )

            documents = int(
                await session.scalar(
                    select(
                        func.count(Document.id)
                    )
                )
                or 0
            )

            documents_24h = int(
                await session.scalar(
                    select(
                        func.count(Document.id)
                    ).where(
                        Document.retrieved_at
                        >= since_24h
                    )
                )
                or 0
            )

            runs_24h = int(
                await session.scalar(
                    select(
                        func.count(
                            IngestionRun.id
                        )
                    ).where(
                        IngestionRun.started_at
                        >= since_24h
                    )
                )
                or 0
            )

            failed_24h = int(
                await session.scalar(
                    select(
                        func.count(
                            IngestionRun.id
                        )
                    ).where(
                        IngestionRun.started_at
                        >= since_24h,
                        IngestionRun.status
                        == "failed",
                    )
                )
                or 0
            )

            successful_7d = int(
                await session.scalar(
                    select(
                        func.count(
                            IngestionRun.id
                        )
                    ).where(
                        IngestionRun.started_at
                        >= since_7d,
                        IngestionRun.status
                        == "succeeded",
                    )
                )
                or 0
            )

            endpoints_without_success = int(
                await session.scalar(
                    select(
                        func.count(
                            SourceEndpoint.id
                        )
                    ).where(
                        SourceEndpoint.status
                        == "active",
                        SourceEndpoint.last_success_at
                        .is_(None),
                    )
                )
                or 0
            )

        failure_rate = (
            failed_24h / runs_24h * 100
            if runs_24h
            else 0.0
        )

        print(
            "Global News Intelligence Platform"
        )
        print(
            f"Generated: {now.isoformat()}"
        )
        print()

        print(
            f"Redis: "
            f"{'OK' if redis_ok else 'FAILED'}"
        )

        print(
            f"Active sources: {active_sources}"
        )

        print(
            f"Active endpoints: {active_endpoints}"
        )

        print(
            f"Active endpoints never successful: "
            f"{endpoints_without_success}"
        )

        print()
        print(
            f"Documents total: {documents:,}"
        )

        print(
            f"Documents retrieved in 24h: "
            f"{documents_24h:,}"
        )

        print()
        print(
            f"Ingestion runs in 24h: "
            f"{runs_24h:,}"
        )

        print(
            f"Failed runs in 24h: "
            f"{failed_24h:,}"
        )

        print(
            f"24h failure rate: "
            f"{failure_rate:.2f}%"
        )

        print(
            f"Successful runs in 7d: "
            f"{successful_7d:,}"
        )


    finally:
        await redis_client.aclose()
        await engine.dispose()    


if __name__ == "__main__":
    asyncio.run(main())