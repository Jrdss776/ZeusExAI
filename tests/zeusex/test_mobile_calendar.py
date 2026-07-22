"""Integração segura do Google Calendar no painel móvel local."""

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.google_calendar import (
    CalendarAccessMode,
    GoogleCalendarConfig,
    GoogleCalendarService,
)
from openjarvis.zeusex.google_calendar_api import GoogleCalendarAPI
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import DASHBOARD_HTML
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler

from test_google_calendar import FakeConnector


def _service(tmp_path, calendar=None):
    return MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedules.db"),
        calendar_api=calendar,
    )


def test_mobile_calendar_is_disabled_by_default(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "GET",
        "/v1/integrations/google-calendar/status",
    )

    assert response.status == 200
    assert response.body["status"]["enabled"] is False


def test_mobile_calendar_preview_never_creates_external_event(tmp_path) -> None:
    connector = FakeConnector()
    calendar = GoogleCalendarAPI(
        GoogleCalendarService(
            connector,
            GoogleCalendarConfig(enabled=True, access_mode=CalendarAccessMode.READ_WRITE),
        )
    )
    response = _service(tmp_path, calendar).dispatch(
        "POST",
        "/v1/integrations/google-calendar/events/preview",
        {
            "title": "Planejamento",
            "start": "2026-07-22T09:00:00-03:00",
            "end": "2026-07-22T10:00:00-03:00",
        },
    )

    assert response.status == 200
    assert response.body["preview"]["external_action_performed"] is False
    assert connector.created == []


def test_mobile_calendar_does_not_expose_creation_route(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "POST",
        "/v1/integrations/google-calendar/events",
        {
            "title": "Não criar",
            "start": "2026-07-22T09:00:00-03:00",
            "end": "2026-07-22T10:00:00-03:00",
        },
    )

    assert response.status == 404


def test_dashboard_exposes_calendar_review_without_browser_storage() -> None:
    assert "Google Calendar" in DASHBOARD_HTML
    assert 'id="calendar-payload"' in DASHBOARD_HTML
    assert 'data-action="calendarPreview"' in DASHBOARD_HTML
    assert "A prévia é local e nunca cria o evento" in DASHBOARD_HTML
    assert "localStorage" not in DASHBOARD_HTML
    assert "sessionStorage" not in DASHBOARD_HTML
