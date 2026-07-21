"""API local somente-leitura para a fundação Google Drive."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.google_drive import GoogleDriveService


@dataclass(frozen=True, slots=True)
class DriveAPIResponse:
    status: int
    body: dict[str, Any]


class GoogleDriveAPI:
    def __init__(self, service: GoogleDriveService) -> None:
        self.service = service

    @staticmethod
    def _error(status: int, message: str) -> DriveAPIResponse:
        return DriveAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, str] | None = None,
    ) -> DriveAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        params = dict(query or {})
        try:
            if verb == "GET" and route == "/v1/integrations/google-drive/status":
                return DriveAPIResponse(200, {"ok": True, "status": self.service.status().to_dict()})
            if verb == "GET" and route == "/v1/integrations/google-drive/files":
                limit = int(params["limit"]) if params.get("limit") else None
                files = self.service.list_files(query=params.get("q"), limit=limit)
                return DriveAPIResponse(200, {"ok": True, "items": [item.to_dict() for item in files]})
            prefix = "/v1/integrations/google-drive/files/"
            if verb == "GET" and route.startswith(prefix):
                file = self.service.get_file(route.removeprefix(prefix))
                if file is None:
                    return self._error(404, "Arquivo não encontrado.")
                return DriveAPIResponse(200, {"ok": True, "file": file.to_dict()})
        except PermissionError as exc:
            return self._error(403, str(exc))
        except (TypeError, ValueError) as exc:
            return self._error(400, str(exc))
        except RuntimeError as exc:
            return self._error(503, str(exc))
        return self._error(404, "Rota não encontrada.")


__all__ = ["DriveAPIResponse", "GoogleDriveAPI"]
