"""API de prévia para configuração futura das integrações Google."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from openjarvis.zeusex.google_setup import build_google_oauth_setup_plan


@dataclass(frozen=True, slots=True)
class GoogleSetupAPIResponse:
    status: int
    body: dict[str, Any]


class GoogleSetupAPI:
    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> GoogleSetupAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        if verb != "POST" or route != "/v1/integrations/google/setup/preview":
            return GoogleSetupAPIResponse(404, {"ok": False, "error": "Rota não encontrada."})
        payload = dict(body or {})
        integrations = payload.get("integrations")
        if not isinstance(integrations, Sequence) or isinstance(
            integrations, (str, bytes, bytearray)
        ):
            return GoogleSetupAPIResponse(
                400,
                {"ok": False, "error": "integrations precisa ser uma lista."},
            )
        try:
            plan = build_google_oauth_setup_plan(
                integrations,
                callback_url=str(
                    payload.get("callback_url")
                    or "http://127.0.0.1:8765/oauth/google/callback"
                ),
            )
        except ValueError as exc:
            return GoogleSetupAPIResponse(400, {"ok": False, "error": str(exc)})
        return GoogleSetupAPIResponse(200, {"ok": True, "plan": plan.to_dict()})


__all__ = ["GoogleSetupAPI", "GoogleSetupAPIResponse"]
