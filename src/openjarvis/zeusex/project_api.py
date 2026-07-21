"""API JSON local para projetos e tarefas do ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.project_service import ProjectService


@dataclass(frozen=True, slots=True)
class ProjectAPIResponse:
    status: int
    body: dict[str, Any]


class ProjectAPIService:
    """Expõe operações locais sem exclusão automática."""

    def __init__(self, service: ProjectService) -> None:
        self.service = service

    @staticmethod
    def _error(status: int, message: str) -> ProjectAPIResponse:
        return ProjectAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        query: Mapping[str, str] | None = None,
    ) -> ProjectAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        payload = dict(body or {})
        params = dict(query or {})

        try:
            if verb == "GET" and route == "/v1/projects":
                items = self.service.projects.list_projects(
                    status=params.get("status"),
                    limit=int(params.get("limit", "50")),
                )
                return ProjectAPIResponse(200, {"ok": True, "items": [item.to_dict() for item in items]})

            if verb == "POST" and route == "/v1/projects":
                project = self.service.create_project(
                    str(payload.get("name") or ""),
                    description=str(payload.get("description") or ""),
                    objective=(str(payload["objective"]) if payload.get("objective") else None),
                    status=str(payload.get("status") or "planned"),
                )
                return ProjectAPIResponse(201, {"ok": True, "project": project.to_dict()})

            if route.startswith("/v1/projects/"):
                parts = route.strip("/").split("/")
                if len(parts) >= 3:
                    project_id = int(parts[2])

                    if verb == "GET" and len(parts) == 3:
                        project = self.service.projects.get_project(project_id)
                        tasks = self.service.projects.list_tasks(project_id)
                        memories = self.service.memories.list(project=project.name, limit=20)
                        return ProjectAPIResponse(
                            200,
                            {
                                "ok": True,
                                "project": project.to_dict(),
                                "tasks": [task.to_dict() for task in tasks],
                                "memories": [memory.to_dict() for memory in memories],
                            },
                        )

                    if verb == "PATCH" and len(parts) == 4 and parts[3] == "status":
                        project = self.service.projects.update_project_status(
                            project_id,
                            str(payload.get("status") or ""),
                        )
                        return ProjectAPIResponse(200, {"ok": True, "project": project.to_dict()})

                    if verb == "GET" and len(parts) == 4 and parts[3] == "tasks":
                        tasks = self.service.projects.list_tasks(
                            project_id,
                            status=params.get("status"),
                            limit=int(params.get("limit", "100")),
                        )
                        return ProjectAPIResponse(
                            200,
                            {"ok": True, "items": [task.to_dict() for task in tasks]},
                        )

                    if verb == "POST" and len(parts) == 4 and parts[3] == "tasks":
                        task = self.service.add_task(
                            project_id,
                            str(payload.get("title") or ""),
                            description=str(payload.get("description") or ""),
                            status=str(payload.get("status") or "todo"),
                            priority=str(payload.get("priority") or "medium"),
                            due_at=(str(payload["due_at"]) if payload.get("due_at") else None),
                        )
                        return ProjectAPIResponse(201, {"ok": True, "task": task.to_dict()})

                    if verb == "POST" and len(parts) == 4 and parts[3] == "decisions":
                        memory_id = self.service.record_decision(
                            project_id,
                            str(payload.get("content") or ""),
                            importance=int(payload.get("importance", 4)),
                        )
                        return ProjectAPIResponse(201, {"ok": True, "memory_id": memory_id})

            if verb == "PATCH" and route.startswith("/v1/tasks/") and route.endswith("/status"):
                parts = route.strip("/").split("/")
                task = self.service.projects.update_task_status(
                    int(parts[2]),
                    str(payload.get("status") or ""),
                )
                return ProjectAPIResponse(200, {"ok": True, "task": task.to_dict()})

        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            return self._error(400, str(exc))

        return self._error(404, "Rota não encontrada.")


__all__ = ["ProjectAPIResponse", "ProjectAPIService"]
