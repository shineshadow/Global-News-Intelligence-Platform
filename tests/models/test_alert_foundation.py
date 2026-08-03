from sqlalchemy import text


async def test_step_26_tables_constraints_and_immutability_triggers(
    database_session_factory,
) -> None:
    expected_tables = {
        "alert_destinations",
        "monitor_alert_destinations",
        "alerts",
        "alert_deliveries",
        "alert_delivery_attempts",
    }
    expected_triggers = {
        "alerts_require_match_provenance",
        "alerts_preserve_immutability",
        "alert_delivery_attempts_preserve_history",
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
                          AND (
                              table_name LIKE 'alert%'
                              OR table_name = 'monitor_alert_destinations'
                          )
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
                                  'alerts_require_match_provenance',
                                  'alerts_preserve_immutability',
                                  'alert_delivery_attempts_preserve_history'
                              )
                        """
                    )
                )
            ).all()
        )
        snapshot_columns = set(
            (
                await session.scalars(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'alert_deliveries'
                        """
                    )
                )
            ).all()
        )

    assert expected_tables <= tables
    assert expected_triggers == triggers
    assert {
        "base_url",
        "topic",
        "auth_token_env_var",
        "request_timeout_seconds",
        "max_attempts",
        "retry_base_seconds",
        "retry_max_seconds",
        "cycle_attempt_count",
    } <= snapshot_columns
