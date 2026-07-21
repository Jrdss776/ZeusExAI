"""API local e somente leitura do Agent Runtime ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.agent_runtime import AgentRuntime


@dataclass(frozen=True, slots=True)
class AgentRuntimeAPIResponse:
    status: int
    body: dict[str, Any]


class AgentRuntimeAPI:
    """Expõe status e criação de planos; não expõe rota de execução."""

    def __init__(self, runtime: AgentRuntime) -> None:
        self.runtime = runtime

    @staticmethod
    def _error(status: int, message: str) -> AgentRuntimeAPIResponse:
        return AgentRuntimeAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> AgentRuntimeAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        payload = dict(body or {})
        try:
            if verb == "GET" and route == "/v1/agent/status":
                return AgentRuntimeAPIResponse(
                    200,
                    {"ok": True, "status": self.runtime.status().to_dict()},
                )
            if verb == "POST" and route == "/v1/agent/plans":
                context = payload.get("context")
                if context is not None and not isinstance(context, Mapping):
                    raise ValueError("context precisa ser um objeto.")
                plan = self.runtime.plan(
                    str(payload.get("command") or ""),
                    context=context,
                )
                return AgentRuntimeAPIResponse(201, {"ok": True, "plan": plan.to_dict()})
            if route.startswith("/v1/agent/execute"):
                return self._error(405, "Execução não está disponível na Fase 17.1.")
        except PermissionError as exc:
            return self._error(403, str(exc))
        except (TypeError, ValueError) as exc:
            return self._error(400, str(exc))
        except RuntimeError as exc:
            return self._error(503, str(exc))
        return self._error(404, "Rota não encontrada.")


__all__ = ["AgentRuntimeAPI", "AgentRuntimeAPIResponse"]
