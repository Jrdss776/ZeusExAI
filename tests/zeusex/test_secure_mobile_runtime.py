"""Testes de autenticação e execução segura da agenda."""

from datetime import datetime, timedelta, timezone

from openjarvis.zeusex.auth import LocalAPIAuthenticator
from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.schedule_executor import ScheduleExecutor
from openjarvis.zeusex.scheduler import SafeScheduler


def test_authenticator_keeps_only_hash_and_checks_bearer() -> None:
    secret = "token-local-seguro-123"
    authenticator = LocalAPIAuthenticator.from_secret(secret)

    assert secret not in authenticator.token_hash
    assert authenticator.authenticate(
        {"Authorization": f"Bearer {secret}"}
    ).allowed is True
    assert authenticator.authenticate(
        {"Authorization": "Bearer incorreto"}
    ).allowed is False
    assert authenticator.authenticate({}).allowed is False


def test_mobile_api_requires_auth_when_configured(tmp_path) -> None:
    secret = "token-local-seguro-123"
    service = MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
        authenticator=LocalAPIAuthenticator.from_secret(secret),
    )

    public_status = service.dispatch("GET", "/v1/status")
    blocked = service.dispatch("GET", "/v1/reports")
    allowed = service.dispatch(
        "GET",
        "/v1/reports",
        headers={"Authorization": f"Bearer {secret}"},
    )

    assert public_status.status == 200
    assert blocked.status == 401
    assert allowed.status == 200


def test_schedule_executor_runs_only_registered_handler(tmp_path) -> None:
    scheduler = SafeScheduler(tmp_path / "schedule.db")
    scheduler.schedule(
        "analysis360",
        {"name": "Produto"},
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    executor = ScheduleExecutor(
        scheduler,
        {"analysis360": lambda payload: payload["name"]},
    )

    outcome = executor.run_once()

    assert outcome.processed is True
    assert outcome.task is not None
    assert outcome.task.status == "completed"
    assert outcome.result == "Produto"


def test_schedule_executor_sanitizes_failure(tmp_path) -> None:
    scheduler = SafeScheduler(tmp_path / "schedule.db")
    scheduler.schedule(
        "campaign",
        {"secret": "não vazar"},
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    def fail(payload):
        raise RuntimeError(payload["secret"])

    outcome = ScheduleExecutor(scheduler, {"campaign": fail}).run_once()

    assert outcome.task is not None
    assert outcome.task.status == "failed"
    assert outcome.task.error == "Falha controlada: RuntimeError."
    assert "não vazar" not in outcome.task.error
