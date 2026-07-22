"""Visão sanitizada das integrações Google do ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from openjarvis.zeusex.gmail import GmailService
from openjarvis.zeusex.google_calendar import GoogleCalendarService
from openjarvis.zeusex.google_drive import GoogleDriveService


@dataclass(frozen=True, slots=True)
class GoogleIntegrationStatus:
    name: str
    enabled: bool
    authenticated: bool
    access_mode: str
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GoogleIntegrationsOverview:
    items: tuple[GoogleIntegrationStatus, ...]
    enabled_count: int
    authenticated_count: int
    ready: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "enabled_count": self.enabled_count,
            "authenticated_count": self.authenticated_count,
            "ready": self.ready,
        }


class GoogleIntegrationsService:
    """Agrega somente estados seguros, sem expor motivos ou credenciais."""

    def __init__(
        self,
        calendar: GoogleCalendarService | None = None,
        gmail: GmailService | None = None,
        drive: GoogleDriveService | None = None,
    ) -> None:
        self.calendar = calendar or GoogleCalendarService()
        self.gmail = gmail or GmailService()
        self.drive = drive or GoogleDriveService()

    @staticmethod
    def _read(name: str, status_reader: Callable[[], Any]) -> GoogleIntegrationStatus:
        try:
            status = status_reader()
        except Exception:
            return GoogleIntegrationStatus(name, False, False, "unavailable", "error")
        enabled = bool(status.enabled)
        authenticated = bool(status.authenticated)
        if not enabled:
            state = "disabled"
        elif not authenticated:
            state = "authentication_required"
        else:
            state = "ready"
        return GoogleIntegrationStatus(
            name=name,
            enabled=enabled,
            authenticated=authenticated,
            access_mode=str(status.access_mode),
            state=state,
        )

    def overview(self) -> GoogleIntegrationsOverview:
        items = (
            self._read("calendar", self.calendar.status),
            self._read("gmail", self.gmail.status),
            self._read("drive", self.drive.status),
        )
        enabled_count = sum(item.enabled for item in items)
        authenticated_count = sum(item.authenticated for item in items)
        return GoogleIntegrationsOverview(
            items,
            enabled_count,
            authenticated_count,
            ready=all(item.state == "ready" for item in items),
        )


__all__ = [
    "GoogleIntegrationStatus",
    "GoogleIntegrationsOverview",
    "GoogleIntegrationsService",
]
