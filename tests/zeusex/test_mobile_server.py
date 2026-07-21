"""Testes do servidor móvel restrito ao loopback."""

from http.client import HTTPConnection
from threading import Thread

import pytest

from openjarvis.zeusex.auth import LocalAPIAuthenticator
from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import (
    MobileServerConfig,
    create_mobile_server,
)
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


def _service(tmp_path):
    return MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
        authenticator=LocalAPIAuthenticator.from_secret(
            "token-local-seguro-123"
        ),
    )


def test_server_rejects_non_loopback_binding() -> None:
    with pytest.raises(ValueError, match="loopback"):
        MobileServerConfig(host="0.0.0.0")
    with pytest.raises(ValueError, match="loopback"):
        MobileServerConfig(host="192.168.1.10")


def test_local_server_serves_dashboard_and_protected_api(tmp_path) -> None:
    server = create_mobile_server(
        _service(tmp_path),
        MobileServerConfig(port=0),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    connection = HTTPConnection(host, port, timeout=3)
    try:
        connection.request("GET", "/")
        dashboard = connection.getresponse()
        html = dashboard.read().decode("utf-8")
        assert dashboard.status == 200
        assert "ZeusEXai Mobile" in html
        assert "localStorage" not in html

        connection.request("GET", "/v1/reports")
        blocked = connection.getresponse()
        blocked.read()
        assert blocked.status == 401

        connection.request(
            "GET",
            "/v1/reports",
            headers={
                "Authorization": "Bearer token-local-seguro-123"
            },
        )
        allowed = connection.getresponse()
        allowed.read()
        assert allowed.status == 200
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_server_rejects_mutating_unknown_methods(tmp_path) -> None:
    server = create_mobile_server(
        _service(tmp_path),
        MobileServerConfig(port=0),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    connection = HTTPConnection(host, port, timeout=3)
    try:
        connection.request("DELETE", "/v1/reports")
        response = connection.getresponse()
        response.read()
        assert response.status == 405
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
