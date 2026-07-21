"""Integração opcional e segura com Google Calendar.

O módulo define contratos locais e não importa SDKs Google obrigatórios. A conexão
real deve ser fornecida pela aplicação hospedeira e permanece desativada por padrão.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, Sequence


class CalendarAccessMode(str, Enum):
    DISABLED = "disabled"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


@dataclass(frozen=True, slots=True)
class CalendarEvent:
    id: str
    title: str
    start: str
    end: str
    location: str = ""
    description: str = ""
    calendar_id: str = "primary"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CalendarEventPreview:
    event: CalendarEvent
    requires_confirmation: bool = True
    external_action_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event.to_dict(),
            "requires_confirmation": self.requires_confirmation,
            "external_action_performed": self.external_action_performed,
        }


@dataclass(frozen=True, slots=True)
class CalendarConnectorStatus:
    enabled: bool
    access_mode: str
    provider: str = "google_calendar"
    authenticated: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GoogleCalendarConfig:
    enabled: bool = False
    access_mode: CalendarAccessMode = CalendarAccessMode.DISABLED
    calendar_id: str = "primary"
    max_results: int = 50

    def __post_init__(self) -> None:
        if self.enabled and self.access_mode is CalendarAccessMode.DISABLED:
            raise ValueError("Integração habilitada exige modo read_only ou read_write.")
        if not 1 <= self.max_results <= 250:
            raise ValueError("max_results precisa estar entre 1 e 250.")
        if not self.calendar_id.strip():
            raise ValueError("calendar_id não pode ficar vazio.")


class GoogleCalendarConnector(Protocol):
    def status(self) -> CalendarConnectorStatus:
        """Retorna o estado da conexão sem expor tokens."""

    def list_events(
        self,
        *,
        time_min: str,
        time_max: str,
        calendar_id: str,
        max_results: int,
        query: str | None = None,
    ) -> Sequence[CalendarEvent]:
        """Lista eventos no intervalo informado."""

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        """Cria evento quando o modo read_write estiver explicitamente ativo."""


class DisabledGoogleCalendarConnector:
    """Conector seguro usado enquanto a integração não foi configurada."""

    def status(self) -> CalendarConnectorStatus:
        return CalendarConnectorStatus(
            enabled=False,
            access_mode=CalendarAccessMode.DISABLED.value,
            authenticated=False,
            reason="Google Calendar não configurado.",
        )

    def list_events(self, **_: Any) -> Sequence[CalendarEvent]:
        raise RuntimeError("Google Calendar não configurado.")

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        del event
        raise RuntimeError("Google Calendar não configurado.")


class GoogleCalendarService:
    """Aplica configuração, limites e confirmação sobre um conector externo."""

    def __init__(
        self,
        connector: GoogleCalendarConnector | None = None,
        config: GoogleCalendarConfig | None = None,
    ) -> None:
        self.connector = connector or DisabledGoogleCalendarConnector()
        self.config = config or GoogleCalendarConfig()

    @staticmethod
    def _validate_interval(time_min: str, time_max: str) -> None:
        start = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
        end = datetime.fromisoformat(time_max.replace("Z", "+00:00"))
        if end <= start:
            raise ValueError("time_max precisa ser posterior a time_min.")

    def status(self) -> CalendarConnectorStatus:
        connector_status = self.connector.status()
        if not self.config.enabled:
            return CalendarConnectorStatus(
                enabled=False,
                access_mode=CalendarAccessMode.DISABLED.value,
                authenticated=connector_status.authenticated,
                reason="Integração desativada na configuração local.",
            )
        return connector_status

    def list_events(
        self,
        *,
        time_min: str,
        time_max: str,
        query: str | None = None,
        limit: int | None = None,
    ) -> list[CalendarEvent]:
        if not self.config.enabled:
            raise PermissionError("Integração com Google Calendar está desativada.")
        if self.config.access_mode not in {
            CalendarAccessMode.READ_ONLY,
            CalendarAccessMode.READ_WRITE,
        }:
            raise PermissionError("Modo de leitura não autorizado.")
        self._validate_interval(time_min, time_max)
        bounded = min(max(1, limit or self.config.max_results), self.config.max_results)
        events = self.connector.list_events(
            time_min=time_min,
            time_max=time_max,
            calendar_id=self.config.calendar_id,
            max_results=bounded,
            query=query.strip() if query and query.strip() else None,
        )
        return list(events)[:bounded]

    def create_event(self, event: CalendarEvent, *, confirmed: bool = False) -> CalendarEvent:
        if not self.config.enabled:
            raise PermissionError("Integração com Google Calendar está desativada.")
        if self.config.access_mode is not CalendarAccessMode.READ_WRITE:
            raise PermissionError("Criação de eventos exige modo read_write.")
        if not confirmed:
            raise PermissionError("Criação de evento exige confirmação explícita.")
        self._validate_interval(event.start, event.end)
        if not event.title.strip():
            raise ValueError("O título do evento não pode ficar vazio.")
        return self.connector.create_event(event)

    def preview_event(self, event: CalendarEvent) -> CalendarEventPreview:
        """Valida uma proposta local sem exigir rede nem criar o evento."""

        self._validate_interval(event.start, event.end)
        if not event.title.strip():
            raise ValueError("O título do evento não pode ficar vazio.")
        normalized = CalendarEvent(
            id="preview",
            title=event.title.strip(),
            start=event.start,
            end=event.end,
            location=event.location.strip(),
            description=event.description.strip(),
            calendar_id=(event.calendar_id.strip() or self.config.calendar_id),
        )
        return CalendarEventPreview(normalized)


__all__ = [
    "CalendarAccessMode",
    "CalendarConnectorStatus",
    "CalendarEvent",
    "CalendarEventPreview",
    "DisabledGoogleCalendarConnector",
    "GoogleCalendarConfig",
    "GoogleCalendarConnector",
    "GoogleCalendarService",
]
