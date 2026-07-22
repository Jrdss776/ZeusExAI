"""API local somente leitura para relatórios históricos de governança."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openjarvis.zeusex.agent_governance_history import AgentGovernanceHistory


@dataclass(slots=True)
class AgentGovernanceHistoryAPI:
    history: AgentGovernanceHistory

    def status(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "mode": "read_only",
            "maximum_period_days": 365,
            "maximum_items": 500,
            "can_approve": False,
            "can_reject": False,
            "can_execute": False,
            "external_actions_enabled": False,
        }

    def report(self, *, days: int = 30, limit: int = 500) -> dict[str, Any]:
        return self.history.build(days=days, limit=limit).to_dict()

    def approve(self, *_: Any, **__: Any) -> None:
        raise PermissionError("O histórico de governança é somente leitura.")

    def execute(self, *_: Any, **__: Any) -> None:
        raise PermissionError("O histórico de governança é somente leitura.")


__all__ = ["AgentGovernanceHistoryAPI"]
