"""API local somente leitura do painel de governança do agente."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openjarvis.zeusex.agent_governance_dashboard import AgentGovernanceDashboard


@dataclass(slots=True)
class AgentGovernanceDashboardAPI:
    dashboard: AgentGovernanceDashboard

    def status(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "mode": "read_only",
            "can_approve": False,
            "can_reject": False,
            "can_execute": False,
            "external_actions_enabled": False,
        }

    def overview(self, *, limit: int = 50) -> dict[str, Any]:
        return self.dashboard.build(limit=limit).to_dict()

    def approve(self, *_: Any, **__: Any) -> None:
        raise PermissionError("O painel de governança é somente leitura.")

    def execute(self, *_: Any, **__: Any) -> None:
        raise PermissionError("O painel de governança é somente leitura.")


__all__ = ["AgentGovernanceDashboardAPI"]
