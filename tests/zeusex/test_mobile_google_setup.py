"""Prévia OAuth Google no painel móvel."""

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import DASHBOARD_HTML
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


def _service(tmp_path):
    return MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedules.db"),
    )


def test_mobile_previews_google_setup_without_connecting(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "POST",
        "/v1/integrations/google/setup/preview",
        {"integrations": ["calendar", "drive"]},
    )
    assert response.status == 200
    assert response.body["plan"]["external_action_performed"] is False


def test_mobile_does_not_expose_google_connect_route(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "POST", "/v1/integrations/google/setup/connect", {}
    )
    assert response.status == 404


def test_dashboard_exposes_google_setup_preview() -> None:
    assert 'id="google-setup-payload"' in DASHBOARD_HTML
    assert 'data-action="googleSetupPreview"' in DASHBOARD_HTML
    assert "Revisar permissões" in DASHBOARD_HTML
