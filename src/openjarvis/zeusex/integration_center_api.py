"""API local somente leitura para a central unificada de integrações."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.integration_center import IntegrationCenterService


@dataclass(frozen=True, slots=True)
class IntegrationCenterAPIResponse:
    status: int
    body: dict[str, Any]


class IntegrationCenterAPI:
    def __init__(self, service: IntegrationCenterService | None = None) -> None:
        self.service = service or IntegrationCenterService()

    @staticmethod
    def _error(status: int, message: str) -> IntegrationCenterAPIResponse:
        return IntegrationCenterAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        query: Mapping[str, str] | None = None,
    ) -> IntegrationCenterAPIResponse:
        del body, query
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        if verb != "GET" or route != "/v1/integrations/overview":
            return self._error(404, "Rota não encontrada.")
        try:
            overview = self.service.overview()
        except Exception:
            return self._error(503, "Não foi possível gerar o diagnóstico das integrações.")
        return IntegrationCenterAPIResponse(200, {"ok": True, "overview": overview.to_dict()})


__all__ = ["IntegrationCenterAPI", "IntegrationCenterAPIResponse"]
