"""Executor controlado das tarefas do agendador local."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from openjarvis.zeusex.scheduler import SafeScheduler, ScheduledTask

ScheduleHandler = Callable[[dict[str, Any]], object]


@dataclass(frozen=True, slots=True)
class ScheduleOutcome:
    task: ScheduledTask | None
    processed: bool
    result: object | None = None


class ScheduleExecutor:
    """Executa somente handlers associados aos tipos da allowlist."""

    def __init__(
        self,
        scheduler: SafeScheduler,
        handlers: Mapping[str, ScheduleHandler],
    ) -> None:
        self.scheduler = scheduler
        self.handlers = dict(handlers)

    def run_once(self) -> ScheduleOutcome:
        task = self.scheduler.claim_due()
        if task is None:
            return ScheduleOutcome(None, False)

        handler = self.handlers.get(task.job_type)
        if handler is None:
            failed = self.scheduler.finish(
                task.id,
                success=False,
                error=f"Handler ausente para {task.job_type}.",
            )
            return ScheduleOutcome(failed, True)

        try:
            result = handler(task.payload)
            completed = self.scheduler.finish(task.id, success=True)
            return ScheduleOutcome(completed, True, result)
        except Exception as exc:
            failed = self.scheduler.finish(
                task.id,
                success=False,
                error=f"Falha controlada: {type(exc).__name__}.",
            )
            return ScheduleOutcome(failed, True)


__all__ = ["ScheduleExecutor", "ScheduleHandler", "ScheduleOutcome"]
