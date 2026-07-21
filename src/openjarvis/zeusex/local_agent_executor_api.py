"""API local do executor controlado da Fase 17.3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openjarvis.zeusex.local_agent_executor import LocalAgentExecutor


@dataclass(slots=True)
class LocalAgentExecutorAPI:
    executor: LocalAgentExecutor

    def status(self) -> dict[str, Any]:
        return self.executor.status()

    def actions(self) -> dict[str, Any]:
        items = list(self.executor.actions())
        return {"items": items, "count": len(items)}

    def execute(self, queue_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        action = str(payload.get("action", "")).strip()
        argument = str(payload.get("argument", ""))
        confirmed = bool(payload.get("confirmed", False))
        receipt = self.executor.execute(
            queue_id,
            action,
            argument=argument,
            confirmed=confirmed,
        )
        return receipt.to_dict()

    def receipts(self, *, queue_id: int | None = None, limit: int = 50) -> dict[str, Any]:
        items = self.executor.list_receipts(queue_id=queue_id, limit=limit)
        return {"items": [item.to_dict() for item in items], "count": len(items)}


__all__ = ["LocalAgentExecutorAPI"]
