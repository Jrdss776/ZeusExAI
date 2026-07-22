"""Consulta segura do Google Drive no painel móvel local."""

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.google_drive import (
    DriveAccessMode,
    GoogleDriveConfig,
    GoogleDriveService,
)
from openjarvis.zeusex.google_drive_api import GoogleDriveAPI
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import DASHBOARD_HTML
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler

from test_google_drive import FakeDriveConnector


def _service(tmp_path, drive=None):
    return MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedules.db"),
        drive_api=drive,
    )


def test_mobile_drive_is_disabled_by_default(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "GET", "/v1/integrations/google-drive/status"
    )
    assert response.status == 200
    assert response.body["status"]["enabled"] is False


def test_mobile_drive_searches_metadata_only(tmp_path) -> None:
    api = GoogleDriveAPI(
        GoogleDriveService(
            FakeDriveConnector(),
            GoogleDriveConfig(True, DriveAccessMode.METADATA_READ),
        )
    )
    response = _service(tmp_path, api).dispatch(
        "GET", "/v1/integrations/google-drive/files?q=vendas&limit=5"
    )
    assert response.status == 200
    assert response.body["items"][0]["name"] == "vendas"


def test_mobile_drive_exposes_file_metadata(tmp_path) -> None:
    api = GoogleDriveAPI(
        GoogleDriveService(
            FakeDriveConnector(),
            GoogleDriveConfig(True, DriveAccessMode.METADATA_READ),
        )
    )
    response = _service(tmp_path, api).dispatch(
        "GET", "/v1/integrations/google-drive/files/file-1"
    )
    assert response.status == 200
    assert response.body["file"]["mime_type"] == "application/pdf"


def test_mobile_drive_does_not_expose_mutation_routes(tmp_path) -> None:
    service = _service(tmp_path)
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        response = service.dispatch(
            method, "/v1/integrations/google-drive/files/file-1"
        )
        assert response.status == 404


def test_dashboard_exposes_metadata_search_without_browser_storage() -> None:
    assert "Google Drive" in DASHBOARD_HTML
    assert 'id="drive-query"' in DASHBOARD_HTML
    assert 'data-action="driveSearch"' in DASHBOARD_HTML
    assert "não baixa, envia, altera ou exclui arquivos" in DASHBOARD_HTML
    assert "localStorage" not in DASHBOARD_HTML
    assert "sessionStorage" not in DASHBOARD_HTML
