from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.calendar import CalendarActor

Priority = Literal["low", "normal", "high", "critical"]


class CalendarOccurrencePolicyOverrideInput(CalendarActor):
    monitoring_priority: Priority | None = None
    expected_news_importance: Priority | None = None
    is_watched: bool | None = None
    reason: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def require_override(self) -> CalendarOccurrencePolicyOverrideInput:
        if self.actor_kind == "operator" and not (
            self.actor_ref and self.actor_ref.strip()
        ):
            raise ValueError("operator policy changes require actor_ref")
        if all(
            value is None
            for value in (
                self.monitoring_priority,
                self.expected_news_importance,
                self.is_watched,
            )
        ):
            raise ValueError("at least one occurrence policy value must be overridden")
        return self


class CalendarOccurrencePolicyOverrideDelete(CalendarActor):
    reason: str = Field(min_length=1, max_length=4000)

    @model_validator(mode="after")
    def require_operator_reference(
        self,
    ) -> CalendarOccurrencePolicyOverrideDelete:
        if self.actor_kind == "operator" and not (
            self.actor_ref and self.actor_ref.strip()
        ):
            raise ValueError("operator policy changes require actor_ref")
        return self


class CalendarOccurrencePolicyHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action_kind: str
    old_monitoring_priority: str | None
    new_monitoring_priority: str | None
    old_expected_news_importance: str | None
    new_expected_news_importance: str | None
    old_is_watched: bool | None
    new_is_watched: bool | None
    reason: str
    actor_kind: str
    actor_ref: str | None
    actor_label: str | None
    changed_at: datetime


class CalendarOccurrencePolicyRead(BaseModel):
    event_id: int
    policy_id: int
    profile_id: int
    occurrence_id: int
    base_monitoring_priority: str
    base_expected_news_importance: str
    base_is_watched: bool
    override_id: int | None
    override_monitoring_priority: str | None
    override_expected_news_importance: str | None
    override_is_watched: bool | None
    effective_monitoring_priority: str
    effective_expected_news_importance: str
    effective_is_watched: bool
    history: list[CalendarOccurrencePolicyHistoryRead]
