from sqlalchemy import func, select

from app.models import OwnerPolicyOverride, OwnerPolicyOverrideEvent
from app.services.owner_policy_service import (
    RETRY_AFTER_ENFORCEMENT,
    OwnerPolicyContext,
    OwnerPolicyPreviewStaleError,
    OwnerPolicyService,
)

ACKNOWLEDGEMENT = "Owner accepts responsibility for this explicit retry policy change."


async def _set(
    session,
    *,
    value: bool,
    scope_type: str,
    scope_identity: str,
    max_uses: int | None = None,
):
    return await OwnerPolicyService().set_override(
        session,
        policy_key=RETRY_AFTER_ENFORCEMENT,
        value=value,
        scope_type=scope_type,
        scope_identity=scope_identity,
        actor="owner:test",
        reason="Exercise exact Owner authority resolution",
        risk_acknowledgement=ACKNOWLEDGEMENT,
        max_uses=max_uses,
    )


async def test_explain_shows_full_matching_chain_without_consuming_authority(
    database_session_factory,
) -> None:
    context = OwnerPolicyContext(
        adapter="feed_parser",
        platform="web",
        credential_ids=(31,),
        origin="https://publisher.example",
        source_id=41,
        endpoint_id=47,
        request_identity="owner-request:53",
    )
    async with database_session_factory() as session, session.begin():
        await _set(session, value=False, scope_type="global", scope_identity="*")
        endpoint = await _set(
            session,
            value=True,
            scope_type="endpoint",
            scope_identity="47",
        )
        request = await _set(
            session,
            value=False,
            scope_type="request",
            scope_identity="owner-request:53",
            max_uses=1,
        )
        decision = await OwnerPolicyService().explain(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            context=context,
            external_observations=({"provider_retry_after": "present"},),
            effective_runtime_decision="allow_by_owner_override",
        )

    assert decision.registered_default is True
    assert decision.effective_value is False
    assert decision.selected_override is not None
    assert decision.selected_override["override_public_id"] == str(request.public_id)
    assert [candidate["scope_type"] for candidate in decision.matching_candidates] == [
        "request",
        "endpoint",
        "global",
    ]
    assert decision.matching_candidates[0]["selected"] is True
    assert decision.uses_would_be_consumed is True
    assert decision.external_observations == ({"provider_retry_after": "present"},)
    assert decision.effective_runtime_decision == "allow_by_owner_override"
    assert endpoint.status == "active"
    assert request.uses_consumed == 0

    async with database_session_factory() as session:
        applied_count = await session.scalar(
            select(func.count())
            .select_from(OwnerPolicyOverrideEvent)
            .where(OwnerPolicyOverrideEvent.event_type.in_(("applied", "consumed")))
        )
    assert applied_count == 0


async def test_preview_is_non_persisting_and_reports_more_specific_authority(
    database_session_factory,
) -> None:
    context = OwnerPolicyContext(endpoint_id=47, request_identity="request:53")
    async with database_session_factory() as session, session.begin():
        request = await _set(
            session,
            value=False,
            scope_type="request",
            scope_identity="request:53",
        )
        before = await session.scalar(select(func.count()).select_from(OwnerPolicyOverride))
        preview = await OwnerPolicyService().preview_override(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            proposed_value=True,
            scope_type="endpoint",
            scope_identity="47",
            context=context,
        )
        after = await session.scalar(select(func.count()).select_from(OwnerPolicyOverride))

    assert before == after == 1
    assert preview.proposal_would_win is False
    assert preview.proposed_decision_context.effective_value is False
    assert preview.proposed_decision_context.selected_override is not None
    assert preview.proposed_decision_context.selected_override["override_public_id"] == str(
        request.public_id
    )
    assert preview.more_specific_overrides_that_still_win[0]["scope_type"] == "request"


async def test_stale_preview_cannot_mutate_owner_authority(
    database_session_factory,
) -> None:
    service = OwnerPolicyService()
    context = OwnerPolicyContext(endpoint_id=47)
    async with database_session_factory() as session, session.begin():
        preview = await service.preview_override(
            session,
            policy_key=RETRY_AFTER_ENFORCEMENT,
            proposed_value=False,
            scope_type="endpoint",
            scope_identity="47",
            context=context,
        )
        await _set(session, value=False, scope_type="global", scope_identity="*")

        try:
            await service.set_override(
                session,
                policy_key=RETRY_AFTER_ENFORCEMENT,
                value=False,
                scope_type="endpoint",
                scope_identity="47",
                actor="owner:test",
                reason="This mutation must reject the stale preview",
                risk_acknowledgement=ACKNOWLEDGEMENT,
                expected_basis_fingerprint=preview.basis_fingerprint,
                basis_context=context,
            )
        except OwnerPolicyPreviewStaleError as exc:
            assert exc.reason_code == "owner_policy.preview_stale"
        else:
            raise AssertionError("stale Owner preview unexpectedly changed authority")

        endpoint_count = await session.scalar(
            select(func.count())
            .select_from(OwnerPolicyOverride)
            .where(OwnerPolicyOverride.scope_type == "endpoint")
        )
    assert endpoint_count == 0
