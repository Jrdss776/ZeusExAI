"""API local para a fundação opcional do Gmail."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from openjarvis.zeusex.gmail import GmailService


@dataclass(frozen=True, slots=True)
class GmailAPIResponse:
    status: int
    body: dict[str, Any]


class GmailAPI:
    def __init__(self, service: GmailService) -> None:
        self.service = service

    @staticmethod
    def _error(status: int, message: str) -> GmailAPIResponse:
        return GmailAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        query: Mapping[str, str] | None = None,
        confirmed: bool = False,
    ) -> GmailAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        payload = dict(body or {})
        params = dict(query or {})
        try:
            if verb == "GET" and route == "/v1/integrations/gmail/status":
                return GmailAPIResponse(200, {"ok": True, "status": self.service.status().to_dict()})
            if verb == "GET" and route == "/v1/integrations/gmail/messages":
                limit = int(params["limit"]) if params.get("limit") else None
                messages = self.service.list_messages(query=params.get("q"), limit=limit)
                return GmailAPIResponse(200, {"ok": True, "items": [item.to_dict() for item in messages]})
            if verb == "POST" and route == "/v1/integrations/gmail/drafts/preview":
                recipients = payload.get("recipients") or []
                if not isinstance(recipients, Sequence) or isinstance(recipients, (str, bytes)):
                    raise ValueError("recipients precisa ser uma lista.")
                preview = self.service.preview_draft(
                    [str(item) for item in recipients],
                    str(payload.get("subject") or ""),
                    str(payload.get("body") or ""),
                )
                return GmailAPIResponse(200, {"ok": True, "preview": preview.to_dict()})
            if verb == "POST" and route == "/v1/integrations/gmail/messages/send":
                recipients = payload.get("recipients") or []
                if not isinstance(recipients, Sequence) or isinstance(recipients, (str, bytes)):
                    raise ValueError("recipients precisa ser uma lista.")
                preview = self.service.preview_draft(
                    [str(item) for item in recipients],
                    str(payload.get("subject") or ""),
                    str(payload.get("body") or ""),
                )
                sent = self.service.send(preview, confirmed=confirmed)
                return GmailAPIResponse(201, {"ok": True, "message": sent.to_dict()})
        except PermissionError as exc:
            return self._error(403, str(exc))
        except (TypeError, ValueError) as exc:
            return self._error(400, str(exc))
        except RuntimeError as exc:
            return self._error(503, str(exc))
        return self._error(404, "Rota não encontrada.")


__all__ = ["GmailAPI", "GmailAPIResponse"]
