"""Testes HTTP da PWA local."""

from http.client import HTTPConnection
from threading import Thread
import json

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import MobileServerConfig, create_mobile_server
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


def test_server_exposes_manifest_icon_and_safe_worker(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
    )
    server = create_mobile_server(service, MobileServerConfig(port=0))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    connection = HTTPConnection(host, port, timeout=3)
    try:
        connection.request("GET", "/manifest.webmanifest")
        manifest_response = connection.getresponse()
        manifest = json.loads(manifest_response.read())
        assert manifest_response.status == 200
        assert manifest["display"] == "standalone"

        connection.request("GET", "/sw.js")
        worker_response = connection.getresponse()
        worker = worker_response.read().decode("utf-8")
        assert worker_response.status == 200
        assert "/v1/" in worker
        assert "Authorization" not in worker

        connection.request("GET", "/icon.svg")
        icon_response = connection.getresponse()
        icon = icon_response.read().decode("utf-8")
        assert icon_response.status == 200
        assert icon.startswith("<svg")

        connection.request("GET", "/")
        dashboard_response = connection.getresponse()
        dashboard = dashboard_response.read().decode("utf-8")
        assert 'rel="manifest"' in dashboard
        assert 'register("/sw.js")' in dashboard
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
