"""Testes da biblioteca, agendador e serviço Android."""

from datetime import datetime, timedelta, timezone

import pytest

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.campaigns import CampaignTemplate
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


class GovernanceAPIStub:
    def status(self):
        return {"enabled": True, "mode": "read_only", "can_execute": False}

    def overview(self, *, limit=50):
        return {"read_only": True, "limit": limit}


class GovernanceHistoryAPIStub:
    def status(self):
        return {"enabled": True, "mode": "read_only", "maximum_period_days": 365}

    def report(self, *, days=30, limit=500):
        if not 1 <= days <= 365:
            raise ValueError("days precisa estar entre 1 e 365.")
        return {"read_only": True, "days": days, "limit": limit}


def test_campaign_template_store_upserts_by_name(tmp_path) -> None:
    store = CampaignTemplateStore(tmp_path / "campaigns.db")
    first = store.save(CampaignTemplate("loja", "Marca A", "Confira.", True))
    updated = store.save(CampaignTemplate("loja", "Marca B", "Veja.", False))

    assert first.id == updated.id
    assert store.get("loja").template.brand == "Marca B"
    assert len(store.list()) == 1


def test_scheduler_claims_only_due_allowed_tasks(tmp_path) -> None:
    scheduler = SafeScheduler(tmp_path / "schedule.db")
    now = datetime.now(timezone.utc)
    due = scheduler.schedule("analysis360", {"id": 1}, now - timedelta(seconds=1))
    scheduler.schedule("campaign", {"id": 2}, now + timedelta(hours=1))

    claimed = scheduler.claim_due(now=now)

    assert claimed is not None
    assert claimed.id == due.id
    assert claimed.status == "running"
    assert claimed.attempts == 1
    assert scheduler.finish(due.id, success=True).status == "completed"


def test_scheduler_rejects_shell_or_publication_jobs(tmp_path) -> None:
    scheduler = SafeScheduler(tmp_path / "schedule.db")
    now = datetime.now(timezone.utc)

    with pytest.raises(ValueError, match="não permitido"):
        scheduler.schedule("shell", {"command": "rm"}, now)
    with pytest.raises(ValueError, match="não permitido"):
        scheduler.schedule("publish_ad", {"id": 1}, now)


def test_mobile_service_builds_and_saves_analysis(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
    )
    response = service.dispatch(
        "POST",
        "/v1/analysis360",
        {
            "save": True,
            "product": {
                "name": "Produto",
                "marketplace": "shopee",
                "sale_price": "100",
                "product_cost": "40",
            },
        },
    )

    assert response.status == 201
    assert response.body["ok"] is True
    assert response.body["report_id"] == 1
    assert (
        service.dispatch("GET", "/v1/reports").body["items"][0]["product_name"]
        == "Produto"
    )


def test_mobile_service_does_not_open_network_listener(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
    )

    response = service.dispatch("GET", "/v1/status")

    assert response.status == 200
    assert response.body["network_listener"] is False
    assert service.dispatch("DELETE", "/v1/reports").status == 404


def test_mobile_service_exposes_read_only_governance(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
        governance_api=GovernanceAPIStub(),
        governance_history_api=GovernanceHistoryAPIStub(),
    )

    status = service.dispatch("GET", "/v1/agent/governance/status")
    overview = service.dispatch("GET", "/v1/agent/governance/overview?limit=25")
    history_status = service.dispatch("GET", "/v1/agent/governance/history/status")
    history = service.dispatch("GET", "/v1/agent/governance/history?days=7&limit=100")

    assert status.status == 200
    assert status.body["mode"] == "read_only"
    assert status.body["can_execute"] is False
    assert overview.body["overview"] == {"read_only": True, "limit": 25}
    assert history_status.body["mode"] == "read_only"
    assert history.body["history"] == {"read_only": True, "days": 7, "limit": 100}


def test_mobile_service_governance_requires_configuration(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
    )

    assert service.dispatch("GET", "/v1/agent/governance/status").status == 503
    assert service.dispatch("GET", "/v1/agent/governance/history").status == 503


def test_mobile_service_rejects_invalid_governance_query(tmp_path) -> None:
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
        governance_api=GovernanceAPIStub(),
        governance_history_api=GovernanceHistoryAPIStub(),
    )

    assert (
        service.dispatch("GET", "/v1/agent/governance/overview?limit=nope").status
        == 400
    )
    assert service.dispatch("GET", "/v1/agent/governance/history?days=0").status == 400
