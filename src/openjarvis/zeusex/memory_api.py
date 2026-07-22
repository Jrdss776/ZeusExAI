"""Adaptador JSON local para a memória inteligente do ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore


@dataclass(frozen=True, slots=True)
class MemoryAPIResponse:
    status: int
    body: dict[str, Any]


class IntelligentMemoryAPI:
    """Expõe somente leitura, busca e criação; não exclui dados automaticamente."""

    def __init__(self, store: IntelligentMemoryStore) -> None:
        self.store = store

    @staticmethod
    def _error(status: int, message: str) -> MemoryAPIResponse:
        return MemoryAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        query: Mapping[str, str] | None = None,
    ) -> MemoryAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        parameters = dict(query or {})

        try:
            if verb == "GET" and route == "/v1/memories":
                category = parameters.get("category") or None
                project = parameters.get("project") or None
                limit = int(parameters.get("limit", "20"))
                items = self.store.list(category=category, project=project, limit=limit)
                return MemoryAPIResponse(
                    200,
                    {"ok": True, "items": [item.to_dict() for item in items]},
                )

            if verb == "GET" and route == "/v1/memories/search":
                search_query = parameters.get("q", "")
                limit = int(parameters.get("limit", "20"))
                items = self.store.search(search_query, limit=limit)
                return MemoryAPIResponse(
                    200,
                    {"ok": True, "items": [item.to_dict() for item in items]},
                )

            if verb == "POST" and route == "/v1/memories":
                payload = dict(body or {})
                memory = self.store.remember(
                    str(payload.get("content") or ""),
                    category=str(payload.get("category") or "general"),
                    project=(str(payload["project"]) if payload.get("project") else None),
                    importance=int(payload.get("importance", 3)),
                )
                return MemoryAPIResponse(
                    201,
                    {"ok": True, "memory": memory.to_dict()},
                )
        except (TypeError, ValueError) as exc:
            return self._error(400, str(exc))

        return self._error(404, "Rota não encontrada.")


__all__ = ["IntelligentMemoryAPI", "MemoryAPIResponse"]
