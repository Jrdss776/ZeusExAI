"""Executor local com políticas, limites e auditoria persistente."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Any, Mapping

from openjarvis.zeusex.execution_audit import ExecutionAuditStore
from openjarvis.zeusex.execution_policy import ActionExecutionPolicy, default_execution_policies
from openjarvis.zeusex.local_agent_executor import LocalAgentExecutor, LocalExecutionReceipt


class PolicyControlledExecutor:
    def __init__(self, executor: LocalAgentExecutor, audit: ExecutionAuditStore, policies: Mapping[str, ActionExecutionPolicy] | None = None) -> None:
        self.executor = executor
        self.audit = audit
        self._policies = dict(policies or default_execution_policies())

    def status(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "mode": "policy_controlled_local",
            "policies": len(self._policies),
            "external_actions_enabled": False,
            "shell_enabled": False,
            "hard_process_termination": False,
        }

    def policies(self) -> tuple[dict[str, Any], ...]:
        return tuple(item.to_dict() for item in sorted(self._policies.values(), key=lambda value: value.action))

    def execute(self, queue_id: int, action: str, *, argument: str = "", confirmed: bool = False) -> LocalExecutionReceipt:
        normalized = action.strip().lower()
        policy = self._policies.get(normalized)
        self.audit.record(queue_id, normalized, "attempt", "pending", "Solicitação recebida.")
        if policy is None:
            self.audit.record(queue_id, normalized, "blocked", "denied", "Ação sem política registrada.")
            raise PermissionError("A ação não possui política de execução registrada.")
        clean_argument = argument.strip()
        if len(clean_argument) > policy.max_argument_length:
            self.audit.record(queue_id, normalized, "blocked", "denied", "Argumento excede o limite.")
            raise ValueError("O argumento excede o limite definido pela política.")
        attempts = self.audit.count(queue_id=queue_id, action=normalized, event="attempt")
        if attempts > policy.max_attempts_per_plan:
            self.audit.record(queue_id, normalized, "blocked", "denied", "Limite de tentativas excedido.")
            raise PermissionError("Limite de tentativas por plano excedido.")
        since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        completed = self.audit.count(action=normalized, event="completed", since=since)
        if completed >= policy.max_executions_per_hour:
            self.audit.record(queue_id, normalized, "blocked", "denied", "Limite por hora excedido.")
            raise PermissionError("Limite de execuções por hora excedido.")
        started = monotonic()
        try:
            receipt = self.executor.execute(queue_id, normalized, argument=clean_argument, confirmed=confirmed)
        except Exception as exc:
            duration_ms = int((monotonic() - started) * 1000)
            self.audit.record(queue_id, normalized, "failed", "denied", type(exc).__name__, duration_ms=duration_ms)
            raise
        duration = monotonic() - started
        duration_ms = int(duration * 1000)
        if duration > policy.timeout_seconds:
            self.audit.record(queue_id, normalized, "timeout", "denied", "Timeout lógico excedido.", duration_ms=duration_ms)
            raise TimeoutError("A execução excedeu o timeout lógico da política.")
        self.audit.record(queue_id, normalized, "completed", "allowed", "Execução local concluída.", duration_ms=duration_ms)
        return receipt


__all__ = ["PolicyControlledExecutor"]
