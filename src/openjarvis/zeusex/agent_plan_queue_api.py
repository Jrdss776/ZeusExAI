"""API local da fila de planos do Agent Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openjarvis.zeusex.agent_plan_queue import AgentPlanQueue, PlanQueueStatus
from openjarvis.zeusex.agent_runtime import AgentRuntime


@dataclass(slots=True)
class AgentPlanQueueAPI:
    runtime: AgentRuntime
    queue: AgentPlanQueue

    def status(self) -> dict[str, Any]:
        pending = self.queue.list(status=PlanQueueStatus.PENDING, limit=200)
        return {
            "enabled": True,
            "mode": "approval_only",
            "pending": len(pending),
            "can_execute": False,
            "external_actions_enabled": False,
        }

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        command = str(payload.get("command", "")).strip()
        ttl_minutes = payload.get("ttl_minutes")
        if ttl_minutes is not None:
            ttl_minutes = int(ttl_minutes)
        plan = self.runtime.plan(command)
        queued = self.queue.enqueue(plan, ttl_minutes=ttl_minutes)
        return queued.to_dict()

    def list(self, *, status: str | None = None, limit: int = 50) -> dict[str, Any]:
        items = self.queue.list(status=status, limit=limit)
        return {"items": [item.to_dict() for item in items], "count": len(items)}

    def get(self, queue_id: int) -> dict[str, Any]:
        return self.queue.get(queue_id).to_dict()

    def approve(self, queue_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        note = str((payload or {}).get("note", ""))
        return self.queue.approve(queue_id, note=note).to_dict()

    def reject(self, queue_id: int, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        note = str((payload or {}).get("note", ""))
        return self.queue.reject(queue_id, note=note).to_dict()

    def execute(self, queue_id: int, payload: dict[str, Any] | None = None) -> None:
        confirmed = bool((payload or {}).get("confirmed", False))
        self.queue.execute(queue_id, confirmed=confirmed)


__all__ = ["AgentPlanQueueAPI"]
