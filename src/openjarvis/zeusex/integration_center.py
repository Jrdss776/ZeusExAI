"""Central unificada e sanitizada das integrações opcionais do ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from openjarvis.zeusex.communication_channels import CommunicationService
from openjarvis.zeusex.github_integration import GitHubService
from openjarvis.zeusex.google_integrations import GoogleIntegrationsService


@dataclass(frozen=True, slots=True)
class IntegrationItem:
    name: str
    category: str
    enabled: bool
    authenticated: bool
    access_mode: str
    state: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntegrationAlert:
    integration: str
    severity: str
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntegrationOverview:
    items: tuple[IntegrationItem, ...]
    alerts: tuple[IntegrationAlert, ...]
    total: int
    enabled: int
    authenticated: int
    ready: int
    overall_state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "alerts": [alert.to_dict() for alert in self.alerts],
            "summary": {
                "total": self.total,
                "enabled": self.enabled,
                "authenticated": self.authenticated,
                "ready": self.ready,
                "alerts": len(self.alerts),
                "overall_state": self.overall_state,
            },
        }


class IntegrationCenterService:
    """Agrega estados seguros sem expor tokens, escopos ou mensagens."""

    def __init__(
        self,
        google: GoogleIntegrationsService | None = None,
        github: GitHubService | None = None,
        communications: CommunicationService | None = None,
    ) -> None:
        self.google = google or GoogleIntegrationsService()
        self.github = github or GitHubService()
        self.communications = communications or CommunicationService({})

    @staticmethod
    def _state(enabled: bool, authenticated: bool) -> str:
        if not enabled:
            return "disabled"
        if not authenticated:
            return "authentication_required"
        return "ready"

    @staticmethod
    def _alert(item: IntegrationItem) -> IntegrationAlert | None:
        if item.state == "error":
            return IntegrationAlert(item.name, "high", "integration_error", "Falha ao consultar a integração.")
        if item.state == "authentication_required":
            return IntegrationAlert(item.name, "medium", "authentication_required", "Autenticação necessária.")
        return None

    def _google_items(self) -> list[IntegrationItem]:
        try:
            overview = self.google.overview()
        except Exception:
            return [IntegrationItem("google", "google", False, False, "unavailable", "error")]
        return [
            IntegrationItem(
                name=f"google_{item.name}",
                category="google",
                enabled=item.enabled,
                authenticated=item.authenticated,
                access_mode=item.access_mode,
                state=item.state,
            )
            for item in overview.items
        ]

    def _github_item(self) -> IntegrationItem:
        try:
            status = self.github.status()
            enabled = bool(status.enabled)
            authenticated = bool(status.authenticated)
            return IntegrationItem(
                "github",
                "development",
                enabled,
                authenticated,
                str(status.access_mode),
                self._state(enabled, authenticated),
            )
        except Exception:
            return IntegrationItem("github", "development", False, False, "unavailable", "error")

    def _communication_items(self) -> list[IntegrationItem]:
        try:
            statuses = self.communications.statuses()
        except Exception:
            return [IntegrationItem("communications", "communication", False, False, "unavailable", "error")]
        return [
            IntegrationItem(
                name=f"channel_{status.channel}",
                category="communication",
                enabled=bool(status.enabled),
                authenticated=bool(status.authenticated),
                access_mode=self.communications.mode.value,
                state=self._state(bool(status.enabled), bool(status.authenticated)),
            )
            for status in statuses
        ]

    def overview(self) -> IntegrationOverview:
        items = tuple(self._google_items() + [self._github_item()] + self._communication_items())
        alerts = tuple(alert for item in items if (alert := self._alert(item)) is not None)
        enabled = sum(item.enabled for item in items)
        authenticated = sum(item.authenticated for item in items)
        ready = sum(item.state == "ready" for item in items)
        if any(item.state == "error" for item in items):
            overall_state = "degraded"
        elif alerts:
            overall_state = "attention_required"
        elif enabled == 0:
            overall_state = "disabled"
        else:
            overall_state = "ready"
        return IntegrationOverview(items, alerts, len(items), enabled, authenticated, ready, overall_state)


__all__ = [
    "IntegrationAlert",
    "IntegrationCenterService",
    "IntegrationItem",
    "IntegrationOverview",
]
