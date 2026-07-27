from sqlalchemy import text


async def test_step_25_tables_and_current_revision_trigger(
    database_session_factory,
) -> None:
    expected_tables = {
        "monitors",
        "monitor_revisions",
        "monitor_revision_geographies",
        "monitor_revision_topics",
        "monitor_revision_entities",
        "monitor_revision_entity_roles",
        "monitor_revision_document_types",
        "monitor_revision_content_formats",
        "monitor_revision_sources",
        "monitor_revision_source_types",
        "monitor_revision_languages",
        "monitor_evaluation_runs",
        "monitor_matches",
    }
    async with database_session_factory() as session:
        tables = set(
            (
                await session.scalars(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name LIKE 'monitor%'
                        """
                    )
                )
            ).all()
        )
        triggers = set(
            (
                await session.scalars(
                    text(
                        """
                        SELECT tgname
                        FROM pg_trigger
                        WHERE NOT tgisinternal
                          AND tgname IN (
                              'monitors_require_current_revision',
                              'revisions_preserve_monitor_current'
                          )
                        """
                    )
                )
            ).all()
        )

    assert expected_tables <= tables
    assert triggers == {
        "monitors_require_current_revision",
        "revisions_preserve_monitor_current",
    }


async def test_step_25_criteria_are_normalized_not_json_metadata(
    database_session_factory,
) -> None:
    async with database_session_factory() as session:
        metadata_columns = set(
            (
                await session.scalars(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'monitor_revisions'
                          AND data_type = 'jsonb'
                        """
                    )
                )
            ).all()
        )
        alert_tables = list(
            (
                await session.scalars(
                    text(
                        """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name IN (
                              'alerts',
                              'alert_deliveries'
                          )
                        """
                    )
                )
            ).all()
        )

    assert metadata_columns == set()
    assert alert_tables == []
