"""Integrações seguras do orquestrador com os serviços locais do ZeusExAI."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from openjarvis.zeusex.command_orchestrator import (
    CommandDomain,
    CommandOrchestrator,
)
from openjarvis.zeusex.mobile_api import APIResponse


class LocalCommandService(Protocol):
    """Contrato mínimo necessário para despachar operações locais."""

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> APIResponse:
        """Executa uma operação na API local."""


def _payload(context: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = context.get("payload", context)
    if not isinstance(payload, Mapping):
        raise ValueError("O contexto do comando precisa conter um payload válido.")
    return payload


def build_mobile_orchestrator(
    service: LocalCommandService,
    *,
    headers: Mapping[str, str] | None = None,
) -> CommandOrchestrator:
    """Cria um orquestrador ligado apenas às rotas locais já autorizadas."""

    def post(path: str):
        def handler(command: str, context: Mapping[str, Any]) -> dict[str, Any]:
            del command
            response = service.dispatch(
                "POST",
                path,
                _payload(context),
                headers=headers,
            )
            return {"status": response.status, "body": response.body}

        return handler

    def get(path: str):
        def handler(command: str, context: Mapping[str, Any]) -> dict[str, Any]:
            del command, context
            response = service.dispatch("GET", path, headers=headers)
            return {"status": response.status, "body": response.body}

        return handler

    return CommandOrchestrator(
        {
            CommandDomain.COMMERCIAL_ANALYSIS: post("/v1/analysis360"),
            CommandDomain.CAMPAIGN: post("/v1/campaign"),
            CommandDomain.ACHADINHOS: post("/v1/achadinhos"),
            CommandDomain.AGENDA: get("/v1/schedules"),
            CommandDomain.DASHBOARD: get("/v1/status"),
        }
    )


__all__ = ["LocalCommandService", "build_mobile_orchestrator"]
