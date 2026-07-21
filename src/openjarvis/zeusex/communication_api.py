"""API local para prévias e envios confirmados por canal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from openjarvis.zeusex.communication_channels import CommunicationService


@dataclass(frozen=True, slots=True)
class CommunicationAPIResponse:
    status: int
    body: dict[str, Any]


class CommunicationAPI:
    def __init__(self, service: CommunicationService) -> None:
        self.service = service

    @staticmethod
    def _error(status: int, message: str) -> CommunicationAPIResponse:
        return CommunicationAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        confirmed: bool = False,
    ) -> CommunicationAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        payload = dict(body or {})
        try:
            if verb == "GET" and route == "/v1/integrations/communications/status":
                return CommunicationAPIResponse(
                    200,
                    {"ok": True, "items": [item.to_dict() for item in self.service.statuses()]},
                )
            if verb == "POST" and route == "/v1/integrations/communications/preview":
                metadata = payload.get("metadata") or {}
                if not isinstance(metadata, Mapping):
                    raise ValueError("metadata precisa ser um objeto.")
                preview = self.service.preview(
                    str(payload.get("channel") or ""),
                    str(payload.get("recipient") or ""),
                    str(payload.get("body") or ""),
                    title=str(payload.get("title") or ""),
                    metadata={str(key): str(value) for key, value in metadata.items()},
                )
                return CommunicationAPIResponse(200, {"ok": True, "preview": preview.to_dict()})
            if verb == "POST" and route == "/v1/integrations/communications/send":
                metadata = payload.get("metadata") or {}
                if not isinstance(metadata, Mapping):
                    raise ValueError("metadata precisa ser um objeto.")
                preview = self.service.preview(
                    str(payload.get("channel") or ""),
                    str(payload.get("recipient") or ""),
                    str(payload.get("body") or ""),
                    title=str(payload.get("title") or ""),
                    metadata={str(key): str(value) for key, value in metadata.items()},
                )
                receipt = self.service.send(preview, confirmed=confirmed)
                return CommunicationAPIResponse(201, {"ok": True, "receipt": receipt.to_dict()})
            if verb == "POST" and route == "/v1/integrations/communications/broadcast":
                raw_items = payload.get("items") or []
                if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes)):
                    raise ValueError("items precisa ser uma lista.")
                previews = []
                for raw in raw_items:
                    if not isinstance(raw, Mapping):
                        raise ValueError("Cada item precisa ser um objeto.")
                    previews.append(
                        self.service.preview(
                            str(raw.get("channel") or ""),
                            str(raw.get("recipient") or ""),
                            str(raw.get("body") or ""),
                            title=str(raw.get("title") or ""),
                        )
                    )
                receipts = self.service.broadcast(previews, confirmed=confirmed)
                return CommunicationAPIResponse(
                    201,
                    {"ok": True, "items": [item.to_dict() for item in receipts]},
                )
        except PermissionError as exc:
            return self._error(403, str(exc))
        except (TypeError, ValueError) as exc:
            return self._error(400, str(exc))
        return self._error(404, "Rota não encontrada.")


__all__ = ["CommunicationAPI", "CommunicationAPIResponse"]
