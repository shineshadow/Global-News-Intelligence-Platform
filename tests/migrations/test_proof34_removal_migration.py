from sqlalchemy import text


async def test_proof34_schema_and_policy_state_are_removed(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        tables = (
            (
                await session.execute(
                    text(
                        """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name LIKE 'acquisition_robots_%'
                    ORDER BY table_name
                    """
                    )
                )
            )
            .scalars()
            .all()
        )
        policy_count = await session.scalar(
            text(
                "SELECT count(*) FROM owner_policy_overrides "
                "WHERE policy_key LIKE 'acquisition.robots.%'"
            )
        )
        robot_bucket_column = await session.scalar(
            text(
                """
                SELECT count(*)
                FROM information_schema.columns
                WHERE table_name = 'acquisition_rate_limit_buckets'
                  AND column_name = 'robots_disallow_until'
                """
            )
        )
        generated_feed_schema = await session.execute(
            text(
                """
                SELECT configuration_schema, provenance
                FROM acquisition_adapters
                WHERE slug IN ('rsshub', 'rss_bridge') AND version = '1'
                ORDER BY slug
                """
            )
        )
        generated_feed_rows = generated_feed_schema.all()

    assert tables == []
    assert policy_count == 0
    assert robot_bucket_column == 0
    assert generated_feed_rows
    for schema, provenance in generated_feed_rows:
        assert schema["required"] == ["internal_service_identity"]
        assert "publisher_target_url" not in schema["properties"]
        assert "robots_target_binding" not in provenance
        assert "proof_34b_migration" not in provenance
