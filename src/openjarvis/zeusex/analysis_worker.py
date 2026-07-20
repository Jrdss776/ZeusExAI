"""Executor controlado da fila comercial do ZeusEXai."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from decimal import Decimal
from typing import Any

from openjarvis.zeusex.analysis_queue import AnalysisJob, AnalysisQueue

JobHandler = Callable[[dict[str, Any]], object]


def _json_safe(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_safe(asdict(value))
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Resultado não serializável: {type(value).__name__}.")


@dataclass(frozen=True, slots=True)
class WorkerOutcome:
    job: AnalysisJob | None
    processed: bool


class AnalysisWorker:
    """Processa um trabalho por chamada e contém falhas no limite da fila."""

    def __init__(
        self,
        queue: AnalysisQueue,
        handlers: Mapping[str, JobHandler],
        *,
        max_attempts: int = 3,
    ) -> None:
        self.queue = queue
        self.handlers = dict(handlers)
        self.max_attempts = max(1, max_attempts)

    def run_once(self) -> WorkerOutcome:
        job = self.queue.claim_next()
        if job is None:
            return WorkerOutcome(job=None, processed=False)

        handler = self.handlers.get(job.marketplace)
        if handler is None:
            failed = self.queue.fail(
                job.id,
                f"Handler ausente para {job.marketplace}.",
                retry=False,
                max_attempts=self.max_attempts,
            )
            return WorkerOutcome(job=failed, processed=True)

        try:
            raw_result = handler(job.payload)
            safe_result = _json_safe(raw_result)
            if not isinstance(safe_result, dict):
                safe_result = {"value": safe_result}
            completed = self.queue.complete(job.id, safe_result)
            return WorkerOutcome(job=completed, processed=True)
        except Exception as exc:
            failed = self.queue.fail(
                job.id,
                f"Falha controlada: {type(exc).__name__}.",
                retry=True,
                max_attempts=self.max_attempts,
            )
            return WorkerOutcome(job=failed, processed=True)


__all__ = ["AnalysisWorker", "JobHandler", "WorkerOutcome"]
