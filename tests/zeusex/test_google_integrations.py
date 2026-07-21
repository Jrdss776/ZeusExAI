"""Central sanitizada das integrações Google."""

from openjarvis.zeusex.gmail import GmailConnectorStatus
from openjarvis.zeusex.google_calendar import CalendarConnectorStatus
from openjarvis.zeusex.google_drive import DriveConnectorStatus
from openjarvis.zeusex.google_integrations import GoogleIntegrationsService


class StatusService:
    def __init__(self, status):
        self._status = status

    def status(self):
        return self._status


class BrokenService:
    def status(self):
        raise RuntimeError("token-secreto-nunca-deve-aparecer")


def test_google_integrations_are_disabled_by_default() -> None:
    overview = GoogleIntegrationsService().overview()
    assert overview.enabled_count == 0
    assert overview.authenticated_count == 0
    assert overview.ready is False
    assert {item.state for item in overview.items} == {"disabled"}


def test_google_integrations_report_ready_services() -> None:
    overview = GoogleIntegrationsService(
        calendar=StatusService(CalendarConnectorStatus(True, "read_only", authenticated=True)),
        gmail=StatusService(GmailConnectorStatus(True, "read_only", True)),
        drive=StatusService(DriveConnectorStatus(True, "metadata_read", True)),
    ).overview()
    assert overview.enabled_count == 3
    assert overview.authenticated_count == 3
    assert overview.ready is True


def test_google_integrations_sanitize_connector_failures() -> None:
    overview = GoogleIntegrationsService(calendar=BrokenService()).overview().to_dict()
    assert overview["items"][0]["state"] == "error"
    assert "token-secreto" not in str(overview)
