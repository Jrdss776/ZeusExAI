"""API JSON local do dashboard inteligente."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.intelligent_dashboard import IntelligentDashboardService


@dataclass(frozen=True, slots=True)
class DashboardAPIResponse:
    status: int
    body: dict[str, Any]


class DashboardAPIService:
    """Expõe apenas leitura agregada do dashboard local."""

    def __init__(self, dashboard: IntelligentDashboardService) -> None:
        self.dashboard = dashboard

    def dispatch(
        self,
        method: str,
        path: str,
        query: Mapping[str, str] | None = None,
    ) -> DashboardAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        if verb != "GET" or route != "/v1/dashboard":
            return DashboardAPIResponse(404, {"ok": False, "error": "Rota não encontrada."})

        try:
            limit = int((query or {}).get("limit", "10"))
            snapshot = self.dashboard.build(limit=limit)
        except (TypeError, ValueError, ArithmeticError) as exc:
            return DashboardAPIResponse(400, {"ok": False, "error": str(exc)})

        return DashboardAPIResponse(
            200,
            {
                "ok": True,
                "dashboard": snapshot.to_dict(),
            },
        )


__all__ = ["DashboardAPIResponse", "DashboardAPIService"]
