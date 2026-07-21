"""Testes das operações comerciais do painel móvel."""

from datetime import datetime, timezone

from openjarvis.zeusex.analysis_queue import AnalysisQueue
from openjarvis.zeusex.auth import LocalAPIAuthenticator
from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import DASHBOARD_HTML
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


def _service(tmp_path):
    token = "token-local-seguro-123"
    headers = {"Authorization": f"Bearer {token}"}
    scheduler = SafeScheduler(tmp_path / "schedule.db")
    queue = AnalysisQueue(tmp_path / "queue.db")
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        scheduler,
        queue=queue,
        authenticator=LocalAPIAuthenticator.from_secret(token),
    )
    return service, headers, scheduler, queue


def _payload():
    return {
        "save": True,
        "product": {
            "name": "Areia biodegradável",
            "marketplace": "shopee",
            "sale_price": "49.90",
            "product_cost": "25",
        },
        "attributes": {"Material": "mandioca"},
    }


def test_panel_api_creates_analysis_and_campaign(tmp_path) -> None:
    service, headers, _, _ = _service(tmp_path)

    analysis = service.dispatch(
        "POST",
        "/v1/analysis360",
        _payload(),
        headers=headers,
    )
    campaign = service.dispatch(
        "POST",
        "/v1/campaign",
        _payload(),
        headers=headers,
    )
    detail = service.dispatch(
        "GET",
        "/v1/reports/1",
        headers=headers,
    )

    assert analysis.status == 201
    assert analysis.body["report_id"] == 1
    assert campaign.status == 200
    assert campaign.body["campaign"]["template"]["brand"] == "Achadinhos do JR"
    assert detail.status == 200
    assert "markdown" in detail.body


def test_panel_api_lists_schedule_and_queue(tmp_path) -> None:
    service, headers, scheduler, queue = _service(tmp_path)
    scheduler.schedule(
        "campaign",
        _payload(),
        datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    queue.enqueue("shopee", {"item_id": 10})

    schedules = service.dispatch("GET", "/v1/schedules", headers=headers)
    jobs = service.dispatch("GET", "/v1/queue", headers=headers)

    assert schedules.status == 200
    assert schedules.body["items"][0]["job_type"] == "campaign"
    assert jobs.status == 200
    assert jobs.body["items"][0]["marketplace"] == "shopee"


def test_dashboard_exposes_local_commercial_actions_without_storage() -> None:
    assert "Criar Análise 360" in DASHBOARD_HTML
    assert "Gerar campanha" in DASHBOARD_HTML
    assert "Fila comercial" in DASHBOARD_HTML
    assert "/v1/schedules" in DASHBOARD_HTML
    assert "localStorage" not in DASHBOARD_HTML
    assert "sessionStorage" not in DASHBOARD_HTML
