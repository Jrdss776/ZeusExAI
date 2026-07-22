"""Central Google no painel móvel local."""

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import DASHBOARD_HTML
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


def test_mobile_exposes_sanitized_google_overview(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedules.db"),
    )
    response = service.dispatch("GET", "/v1/integrations/google/status")
    assert response.status == 200
    assert len(response.body["overview"]["items"]) == 3


def test_mobile_google_overview_is_read_only(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedules.db"),
    )
    assert service.dispatch("POST", "/v1/integrations/google/status").status == 404


def test_dashboard_exposes_google_integration_center() -> None:
    assert "Central Google" in DASHBOARD_HTML
    assert 'data-action="googleStatus"' in DASHBOARD_HTML
    assert "Diagnóstico sanitizado" in DASHBOARD_HTML
