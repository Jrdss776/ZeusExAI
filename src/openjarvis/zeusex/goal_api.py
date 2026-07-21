"""Camada JSON local para objetivos mensuráveis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.goal_service import GoalService
from openjarvis.zeusex.goals import GoalStore


@dataclass(frozen=True, slots=True)
class GoalAPIResponse:
    status: int
    body: dict[str, Any]


class GoalAPIService:
    def __init__(self, goals: GoalStore, service: GoalService) -> None:
        self.goals = goals
        self.service = service

    @staticmethod
    def _error(status: int, message: str) -> GoalAPIResponse:
        return GoalAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        query: Mapping[str, Any] | None = None,
    ) -> GoalAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        payload = dict(body or {})
        params = dict(query or {})
        try:
            if verb == "GET" and route == "/v1/goals":
                project_id = params.get("project_id")
                goals = self.goals.list_goals(
                    project_id=int(project_id) if project_id is not None else None,
                    status=str(params["status"]) if params.get("status") else None,
                    limit=int(params.get("limit", 100)),
                )
                return GoalAPIResponse(200, {"ok": True, "items": [g.to_dict() for g in goals]})

            if verb == "POST" and route == "/v1/goals":
                goal = self.service.create_goal(
                    str(payload.get("title") or ""),
                    metric=str(payload.get("metric") or ""),
                    target=float(payload["target"]),
                    baseline=float(payload.get("baseline", 0)),
                    current=float(payload["current"]) if payload.get("current") is not None else None,
                    project_id=int(payload["project_id"]) if payload.get("project_id") is not None else None,
                    description=str(payload.get("description") or ""),
                    direction=str(payload.get("direction") or "increase"),
                    unit=str(payload.get("unit") or ""),
                    status=str(payload.get("status") or "planned"),
                    due_at=str(payload["due_at"]) if payload.get("due_at") else None,
                )
                return GoalAPIResponse(201, {"ok": True, "goal": goal.to_dict()})

            if route.startswith("/v1/goals/"):
                parts = route.strip("/").split("/")
                goal_id = int(parts[2])
                if verb == "GET" and len(parts) == 3:
                    return GoalAPIResponse(200, {"ok": True, **self.service.summary(goal_id)})
                if verb == "PATCH" and len(parts) == 4 and parts[3] == "status":
                    goal = self.goals.update_status(goal_id, str(payload.get("status") or ""))
                    return GoalAPIResponse(200, {"ok": True, "goal": goal.to_dict()})
                if verb == "POST" and len(parts) == 4 and parts[3] == "checkins":
                    checkin = self.service.check_in(
                        goal_id,
                        float(payload["value"]),
                        note=str(payload.get("note") or ""),
                    )
                    goal = self.goals.get_goal(goal_id)
                    return GoalAPIResponse(
                        201,
                        {"ok": True, "checkin": checkin.to_dict(), "goal": goal.to_dict()},
                    )
        except KeyError as exc:
            return self._error(404, str(exc))
        except (TypeError, ValueError, ArithmeticError) as exc:
            return self._error(400, str(exc))
        return self._error(404, "Rota não encontrada.")


__all__ = ["GoalAPIResponse", "GoalAPIService"]
