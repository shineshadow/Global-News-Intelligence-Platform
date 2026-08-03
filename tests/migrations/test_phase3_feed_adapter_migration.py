from sqlalchemy import text


async def test_feed_adapter_seed_is_exact_and_does_not_cut_over_endpoints(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        adapter = (
            await session.execute(
                text(
                    """
                    SELECT slug, version, implementation, status,
                           configuration_schema,
                           provenance ->> 'activation_scope'
                    FROM acquisition_adapters
                    WHERE slug = 'feed_parser' AND version = '1'
                    """
                )
            )
        ).one()
        assert tuple(adapter) == (
            "feed_parser",
            "1",
            "ingestion.adapters.feed_parser:FeedParserAdapter",
            "active",
            {"type": "object", "properties": {}, "additionalProperties": False},
            "registry-only-no-endpoint-cutover",
        )
        compatibility = (
            await session.execute(
                text(
                    """
                    SELECT endpoint_type, endpoint_format,
                           acquisition_method, platform_key
                    FROM acquisition_adapter_compatibilities AS compatibility
                    JOIN acquisition_adapters AS adapter
                      ON adapter.id = compatibility.adapter_id
                    WHERE adapter.slug = 'feed_parser' AND adapter.version = '1'
                    ORDER BY endpoint_format
                    """
                )
            )
        ).all()
        assert [tuple(row) for row in compatibility] == [
            ("feed", "atom", "feed_parser", "*"),
            ("feed", "rss", "feed_parser", "*"),
        ]
        capabilities = (
            await session.execute(
                text(
                    """
                    SELECT format.slug, capability.identification_supported,
                           capability.safe_parser_supported,
                           capability.safe_extraction_supported
                    FROM acquisition_adapter_artifact_capabilities AS capability
                    JOIN acquisition_adapters AS adapter
                      ON adapter.id = capability.adapter_id
                    JOIN artifact_formats AS format
                      ON format.id = capability.artifact_format_id
                    WHERE adapter.slug = 'feed_parser' AND adapter.version = '1'
                    ORDER BY format.slug
                    """
                )
            )
        ).all()
        assert [tuple(row) for row in capabilities] == [
            ("atom", True, True, False),
            ("rss", True, True, False),
        ]
        assert (
            await session.scalar(text("SELECT count(*) FROM acquisition_endpoint_configurations"))
            == 0
        )
