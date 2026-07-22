from types import SimpleNamespace

from openjarvis.zeusex.communication_channels import (
    ChannelStatus,
    CommunicationAccessMode,
    CommunicationChannel,
    CommunicationService,
)
from openjarvis.zeusex.integration_center import IntegrationCenterService
from openjarvis.zeusex.integration_center_api import IntegrationCenterAPI


class FakeGoogle:
    def overview(self):
        return SimpleNamespace(
            items=(
                SimpleNamespace(
                    name="calendar",
                    enabled=True,
                    authenticated=True,
                    access_mode="read_only",
                    state="ready",
                ),
                SimpleNamespace(
                    name="gmail",
                    enabled=True,
                    authenticated=False,
                    access_mode="read_only",
                    state="authentication_required",
                ),
                SimpleNamespace(
                    name="drive",
                    enabled=False,
                    authenticated=False,
                    access_mode="disabled",
                    state="disabled",
                ),
            )
        )


class FakeGitHub:
    def status(self):
        return SimpleNamespace(enabled=True, authenticated=True, access_mode="read_only")


class FakeChannelConnector:
    def __init__(self, channel: str, *, enabled: bool, authenticated: bool) -> None:
        self.channel = channel
        self.enabled = enabled
        self.authenticated = authenticated

    def status(self):
        return ChannelStatus(self.channel, self.enabled, self.authenticated)

    def send(self, preview):
        raise AssertionError("A central não pode enviar mensagens.")


class BrokenGoogle:
    def overview(self):
        raise RuntimeError("indisponível")


def build_service() -> IntegrationCenterService:
    communications = CommunicationService(
        {
            CommunicationChannel.LOCAL: FakeChannelConnector("local", enabled=True, authenticated=True),
            CommunicationChannel.WHATSAPP: FakeChannelConnector(
                "whatsapp", enabled=True, authenticated=False
            ),
        },
        mode=CommunicationAccessMode.PREVIEW_ONLY,
    )
    return IntegrationCenterService(FakeGoogle(), FakeGitHub(), communications)


def test_overview_aggregates_integrations_and_alerts() -> None:
    overview = build_service().overview()

    assert overview.total == 8
    assert overview.enabled == 5
    assert overview.authenticated == 3
    assert overview.ready == 3
    assert overview.overall_state == "attention_required"
    assert {alert.integration for alert in overview.alerts} == {"google_gmail", "channel_whatsapp"}


def test_disabled_integrations_do_not_generate_alerts() -> None:
    overview = build_service().overview()
    disabled = {item.name for item in overview.items if item.state == "disabled"}

    assert "google_drive" in disabled
    assert "channel_telegram" in disabled
    assert all(alert.integration not in disabled for alert in overview.alerts)


def test_component_failure_degrades_overview_without_leaking_exception() -> None:
    service = IntegrationCenterService(BrokenGoogle(), FakeGitHub(), CommunicationService({}))
    overview = service.overview()

    assert overview.overall_state == "degraded"
    assert overview.items[0].name == "google"
    assert overview.items[0].state == "error"
    assert overview.alerts[0].code == "integration_error"


def test_api_is_read_only() -> None:
    api = IntegrationCenterAPI(build_service())

    response = api.dispatch("GET", "/v1/integrations/overview")
    blocked = api.dispatch("POST", "/v1/integrations/overview", {})

    assert response.status == 200
    assert response.body["overview"]["summary"]["overall_state"] == "attention_required"
    assert blocked.status == 404
