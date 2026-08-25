"""Add the Proof 34A.1 unavailable-evidence information contract.

Revision ID: e5a7c9d1f3b2
Revises: c2f4a6b8d0e1
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5a7c9d1f3b2"
down_revision: str | None = "c2f4a6b8d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FAILURE_PHASE_CHECK = (
    "failure_phase IS NULL OR failure_phase IN "
    "('retrieval', 'validation', 'parsing', 'evaluation', 'evidence_binding')"
)
RETRYABLE_CHECK = "retryable IS NULL OR retryable IN ('true', 'false', 'unknown')"
OWNER_SUMMARY_CHECK = (
    "owner_summary IS NULL OR (char_length(owner_summary) BETWEEN 1 AND 500 "
    "AND owner_summary !~ '[[:cntrl:]]')"
)
REASON_PHASE_CHECK = (
    "unavailable_reason IS NULL OR "
    "(failure_phase = 'retrieval' AND unavailable_reason IN "
    "('http_not_found', 'http_client_error', 'http_server_error', 'dns_failure', "
    "'connection_failure', 'connection_timeout', 'read_timeout', 'tls_failure', "
    "'redirect_limit_reached', 'response_too_large')) OR "
    "(failure_phase = 'validation' AND unavailable_reason IN "
    "('redirect_destination_rejected', 'egress_guard_rejected', "
    "'parser_provenance_untrusted')) OR "
    "(failure_phase = 'parsing' AND unavailable_reason IN "
    "('robots_body_empty', 'robots_body_malformed', 'parser_failure')) OR "
    "(failure_phase = 'evaluation' AND unavailable_reason = 'evaluation_failure') OR "
    "(failure_phase = 'evidence_binding' AND unavailable_reason IN "
    "('evidence_missing', 'evidence_stale', 'evidence_target_mismatch', "
    "'evidence_user_agent_mismatch', 'evidence_untrusted'))"
)


def _add_information_columns(table_name: str) -> None:
    op.add_column(table_name, sa.Column("failure_phase", sa.String(length=30), nullable=True))
    op.add_column(
        table_name,
        sa.Column("unavailable_reason", sa.String(length=64), nullable=True),
    )
    op.add_column(table_name, sa.Column("retryable", sa.String(length=10), nullable=True))
    op.add_column(table_name, sa.Column("owner_summary", sa.String(length=500), nullable=True))


def upgrade() -> None:
    connection = op.get_bind()
    unclassified = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM acquisition_robots_snapshots
                WHERE retrieval_state NOT IN ('retrieved', 'not_modified')
                   OR parse_state NOT IN ('parsed', 'empty')
            ) OR EXISTS (
                SELECT 1
                FROM acquisition_robots_evaluations
                WHERE external_decision = 'unavailable'
            )
            """
        )
    ).scalar_one()
    if unclassified:
        raise RuntimeError(
            "Cannot add the Proof 34A.1 information contract while unclassified "
            "unavailable robots evidence exists. Classify and preserve that evidence first."
        )

    _add_information_columns("acquisition_robots_snapshots")
    _add_information_columns("acquisition_robots_evaluations")

    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_unavailable_information_required"),
        "acquisition_robots_snapshots",
        "((retrieval_state IN ('retrieved', 'not_modified') "
        "AND parse_state IN ('parsed', 'empty') AND failure_phase IS NULL) OR "
        "((retrieval_state NOT IN ('retrieved', 'not_modified') "
        "OR parse_state NOT IN ('parsed', 'empty')) AND failure_phase IS NOT NULL))",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_unavailable_information_complete"),
        "acquisition_robots_snapshots",
        "(failure_phase IS NULL AND unavailable_reason IS NULL AND retryable IS NULL "
        "AND owner_summary IS NULL) OR "
        "(failure_phase IS NOT NULL AND unavailable_reason IS NOT NULL "
        "AND retryable IS NOT NULL AND owner_summary IS NOT NULL)",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_failure_phase"),
        "acquisition_robots_snapshots",
        FAILURE_PHASE_CHECK,
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_retryable"),
        "acquisition_robots_snapshots",
        RETRYABLE_CHECK,
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_owner_summary_bounded_sanitized"),
        "acquisition_robots_snapshots",
        OWNER_SUMMARY_CHECK,
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_unavailable_reason_phase"),
        "acquisition_robots_snapshots",
        REASON_PHASE_CHECK,
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_http_not_found_status"),
        "acquisition_robots_snapshots",
        "unavailable_reason <> 'http_not_found' OR http_status IN (404, 410)",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_http_client_error_status"),
        "acquisition_robots_snapshots",
        "unavailable_reason <> 'http_client_error' OR "
        "(http_status BETWEEN 400 AND 499 AND http_status NOT IN (404, 410))",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_snapshots_http_server_error_status"),
        "acquisition_robots_snapshots",
        "unavailable_reason <> 'http_server_error' OR http_status BETWEEN 500 AND 599",
    )

    op.create_check_constraint(
        op.f("ck_acquisition_robots_evaluations_unavailable_information_matches_decision"),
        "acquisition_robots_evaluations",
        "(external_decision = 'unavailable' AND failure_phase IS NOT NULL "
        "AND unavailable_reason IS NOT NULL AND retryable IS NOT NULL "
        "AND owner_summary IS NOT NULL) OR "
        "(external_decision <> 'unavailable' AND failure_phase IS NULL "
        "AND unavailable_reason IS NULL AND retryable IS NULL AND owner_summary IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_evaluations_failure_phase"),
        "acquisition_robots_evaluations",
        FAILURE_PHASE_CHECK,
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_evaluations_retryable"),
        "acquisition_robots_evaluations",
        RETRYABLE_CHECK,
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_evaluations_owner_summary_bounded_sanitized"),
        "acquisition_robots_evaluations",
        OWNER_SUMMARY_CHECK,
    )
    op.create_check_constraint(
        op.f("ck_acquisition_robots_evaluations_unavailable_reason_phase"),
        "acquisition_robots_evaluations",
        REASON_PHASE_CHECK,
    )


def downgrade() -> None:
    connection = op.get_bind()
    retained = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM acquisition_robots_snapshots
                WHERE failure_phase IS NOT NULL
                   OR unavailable_reason IS NOT NULL
                   OR retryable IS NOT NULL
                   OR owner_summary IS NOT NULL
            ) OR EXISTS (
                SELECT 1 FROM acquisition_robots_evaluations
                WHERE failure_phase IS NOT NULL
                   OR unavailable_reason IS NOT NULL
                   OR retryable IS NOT NULL
                   OR owner_summary IS NOT NULL
            )
            """
        )
    ).scalar_one()
    if retained:
        raise RuntimeError(
            "Cannot downgrade Proof 34A.1 while retained unavailable-information evidence exists."
        )

    snapshot_constraints = (
        "http_server_error_status",
        "http_client_error_status",
        "http_not_found_status",
        "unavailable_reason_phase",
        "owner_summary_bounded_sanitized",
        "retryable",
        "failure_phase",
        "unavailable_information_complete",
        "unavailable_information_required",
    )
    for suffix in snapshot_constraints:
        op.drop_constraint(
            op.f(f"ck_acquisition_robots_snapshots_{suffix}"),
            "acquisition_robots_snapshots",
            type_="check",
        )

    evaluation_constraints = (
        "unavailable_reason_phase",
        "owner_summary_bounded_sanitized",
        "retryable",
        "failure_phase",
        "unavailable_information_matches_decision",
    )
    for suffix in evaluation_constraints:
        op.drop_constraint(
            op.f(f"ck_acquisition_robots_evaluations_{suffix}"),
            "acquisition_robots_evaluations",
            type_="check",
        )

    for table_name in (
        "acquisition_robots_evaluations",
        "acquisition_robots_snapshots",
    ):
        op.drop_column(table_name, "owner_summary")
        op.drop_column(table_name, "retryable")
        op.drop_column(table_name, "unavailable_reason")
        op.drop_column(table_name, "failure_phase")
