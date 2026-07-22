"""API local para a integração opcional com Google Calendar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.google_calendar import CalendarEvent, GoogleCalendarService


@dataclass(frozen=True, slots=True)
class CalendarAPIResponse:
    status: int
    body: dict[str, Any]


class GoogleCalendarAPI:
    """Expõe operações controladas sem persistir credenciais."""

    def __init__(self, service: GoogleCalendarService) -> None:
        self.service = service

    @staticmethod
    def _error(status: int, message: str) -> CalendarAPIResponse:
        return CalendarAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        query: Mapping[str, str] | None = None,
        confirmed: bool = False,
    ) -> CalendarAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        params = dict(query or {})
        payload = dict(body or {})

        try:
            if verb == "GET" and route == "/v1/integrations/google-calendar/status":
                return CalendarAPIResponse(
                    200,
                    {"ok": True, "status": self.service.status().to_dict()},
                )

            if verb == "GET" and route == "/v1/integrations/google-calendar/events":
                time_min = params.get("time_min", "")
                time_max = params.get("time_max", "")
                if not time_min or not time_max:
                    raise ValueError("time_min e time_max são obrigatórios.")
                limit_text = params.get("limit")
                events = self.service.list_events(
                    time_min=time_min,
                    time_max=time_max,
                    query=params.get("q"),
                    limit=int(limit_text) if limit_text else None,
                )
                return CalendarAPIResponse(
                    200,
                    {"ok": True, "items": [event.to_dict() for event in events]},
                )

            if verb == "POST" and route == "/v1/integrations/google-calendar/events":
                event = CalendarEvent(
                    id=str(payload.get("id") or "pending"),
                    title=str(payload.get("title") or ""),
                    start=str(payload.get("start") or ""),
                    end=str(payload.get("end") or ""),
                    location=str(payload.get("location") or ""),
                    description=str(payload.get("description") or ""),
                    calendar_id=str(payload.get("calendar_id") or "primary"),
                )
                created = self.service.create_event(event, confirmed=confirmed)
                return CalendarAPIResponse(201, {"ok": True, "event": created.to_dict()})

            if verb == "POST" and route == "/v1/integrations/google-calendar/events/preview":
                event = CalendarEvent(
                    id="preview",
                    title=str(payload.get("title") or ""),
                    start=str(payload.get("start") or ""),
                    end=str(payload.get("end") or ""),
                    location=str(payload.get("location") or ""),
                    description=str(payload.get("description") or ""),
                    calendar_id=str(payload.get("calendar_id") or "primary"),
                )
                preview = self.service.preview_event(event)
                return CalendarAPIResponse(200, {"ok": True, "preview": preview.to_dict()})
        except PermissionError as exc:
            return self._error(403, str(exc))
        except (TypeError, ValueError) as exc:
            return self._error(400, str(exc))
        except RuntimeError as exc:
            return self._error(503, str(exc))

        return self._error(404, "Rota não encontrada.")


__all__ = ["CalendarAPIResponse", "GoogleCalendarAPI"]
