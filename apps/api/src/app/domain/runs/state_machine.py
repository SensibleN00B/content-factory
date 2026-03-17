from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.infrastructure.db.models import Run

RunStatus = Literal["pending", "collecting", "processing", "scoring", "completed", "failed"]

ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    "pending": {"collecting", "failed"},
    "collecting": {"processing", "failed"},
    "processing": {"scoring", "failed"},
    "scoring": {"completed", "failed"},
    "completed": set(),
    "failed": set(),
}


class InvalidRunTransitionError(ValueError):
    """Raised when attempting a disallowed run status transition."""


class RunStateMachine:
    def transition(
        self,
        *,
        db_session: Session,
        run: Run,
        target_status: RunStatus,
        now: datetime | None = None,
        error_summary: str | None = None,
    ) -> Run:
        current_status = self._as_run_status(run.status)
        allowed_targets = ALLOWED_TRANSITIONS[current_status]

        if target_status not in allowed_targets:
            raise InvalidRunTransitionError(
                f"Invalid transition: '{current_status}' -> '{target_status}'"
            )

        now_utc = now or datetime.now(UTC)
        run.status = target_status

        if target_status == "collecting" and run.started_at is None:
            run.started_at = now_utc

        if target_status in {"completed", "failed"}:
            run.finished_at = now_utc

        if target_status == "failed":
            run.error_summary = error_summary

        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)
        return run

    @staticmethod
    def _as_run_status(value: str) -> RunStatus:
        if value not in ALLOWED_TRANSITIONS:
            raise InvalidRunTransitionError(f"Unknown run status '{value}'")
        return value  # type: ignore[return-value]
