"""Contratos leves e seguros para tarefas da agente Vampira."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol, Sequence

from openjarvis.zeusex.productivity_audit import (
    ProductivityAuditSink,
    build_productivity_audit_from_env,
)


class TaskAccessMode(str, Enum):
    DISABLED = "disabled"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


@dataclass(frozen=True, slots=True)
class ProductivityTask:
    id: str
    title: str
    due_at: str = ""
    notes: str = ""
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProductivityTaskConfig:
    enabled: bool = False
    access_mode: TaskAccessMode = TaskAccessMode.DISABLED
    max_results: int = 100

    def __post_init__(self) -> None:
        if self.enabled and self.access_mode is TaskAccessMode.DISABLED:
            raise ValueError("Tarefas habilitadas exigem modo read_only ou read_write.")
        if not 1 <= self.max_results <= 500:
            raise ValueError("max_results precisa estar entre 1 e 500.")


class ProductivityTaskConnector(Protocol):
    def list_tasks(self, *, max_results: int) -> Sequence[ProductivityTask]: ...
    def create_task(self, task: ProductivityTask) -> ProductivityTask: ...
    def complete_task(self, task_id: str) -> ProductivityTask: ...
    def delete_task(self, task_id: str) -> None: ...


class DisabledProductivityTaskConnector:
    def list_tasks(self, **_: Any) -> Sequence[ProductivityTask]:
        raise RuntimeError("Integração de tarefas não configurada.")

    def create_task(self, task: ProductivityTask) -> ProductivityTask:
        del task
        raise RuntimeError("Integração de tarefas não configurada.")

    def complete_task(self, task_id: str) -> ProductivityTask:
        del task_id
        raise RuntimeError("Integração de tarefas não configurada.")

    def delete_task(self, task_id: str) -> None:
        del task_id
        raise RuntimeError("Integração de tarefas não configurada.")


class ProductivityTaskService:
    def __init__(
        self,
        connector: ProductivityTaskConnector | None = None,
        config: ProductivityTaskConfig | None = None,
        audit: ProductivityAuditSink | None = None,
    ) -> None:
        self.connector = connector or DisabledProductivityTaskConnector()
        self.config = config or ProductivityTaskConfig()
        self.audit = audit or build_productivity_audit_from_env()

    def _require_read(self) -> None:
        if not self.config.enabled or self.config.access_mode is TaskAccessMode.DISABLED:
            raise PermissionError("Integração de tarefas está desativada.")

    def _require_write(self, action: str, task_id: str, confirmed: bool) -> None:
        if not self.config.enabled or self.config.access_mode is not TaskAccessMode.READ_WRITE:
            self.audit.record(action, "blocked", "write_mode_required", resource_id=task_id)
            raise PermissionError("Ação exige modo read_write.")
        if not confirmed:
            self.audit.record(action, "blocked", "explicit_confirmation_required", resource_id=task_id)
            raise PermissionError("Ação em tarefa exige confirmação explícita.")

    def list_tasks(self, *, limit: int | None = None) -> list[ProductivityTask]:
        self._require_read()
        bounded = min(max(1, limit or self.config.max_results), self.config.max_results)
        return list(self.connector.list_tasks(max_results=bounded))[:bounded]

    def create(self, title: str, *, due_at: str = "", notes: str = "") -> ProductivityTask:
        if not self.config.enabled or self.config.access_mode is not TaskAccessMode.READ_WRITE:
            raise PermissionError("Criação de tarefa exige modo read_write.")
        clean_title = title.strip()
        if not clean_title or len(clean_title) > 300:
            raise ValueError("O título precisa ter entre 1 e 300 caracteres.")
        return self.connector.create_task(
            ProductivityTask("pending", clean_title, due_at.strip(), notes.strip())
        )

    def complete(self, task_id: str, *, confirmed: bool = False) -> ProductivityTask:
        clean_id = task_id.strip()
        self._require_write("task.complete", clean_id, confirmed)
        result = self.connector.complete_task(clean_id)
        self.audit.record("task.complete", "allowed", "explicitly_confirmed", resource_id=clean_id)
        return result

    def delete(self, task_id: str, *, confirmed: bool = False) -> None:
        clean_id = task_id.strip()
        self._require_write("task.delete", clean_id, confirmed)
        self.connector.delete_task(clean_id)
        self.audit.record("task.delete", "allowed", "explicitly_confirmed", resource_id=clean_id)


__all__ = [
    "DisabledProductivityTaskConnector",
    "ProductivityTask",
    "ProductivityTaskConfig",
    "ProductivityTaskConnector",
    "ProductivityTaskService",
    "TaskAccessMode",
]
