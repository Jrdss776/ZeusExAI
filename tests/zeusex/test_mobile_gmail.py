"""Triagem e prévia segura do Gmail no painel móvel local."""

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.gmail import GmailAccessMode, GmailConfig, GmailService
from openjarvis.zeusex.gmail_api import GmailAPI
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.mobile_server import DASHBOARD_HTML
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler

from test_gmail import FakeGmailConnector


def _service(tmp_path, gmail=None):
    return MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedules.db"),
        gmail_api=gmail,
    )


def test_mobile_gmail_is_disabled_by_default(tmp_path) -> None:
    response = _service(tmp_path).dispatch("GET", "/v1/integrations/gmail/status")
    assert response.status == 200
    assert response.body["status"]["enabled"] is False


def test_mobile_gmail_lists_unread_messages_read_only(tmp_path) -> None:
    connector = FakeGmailConnector()
    api = GmailAPI(GmailService(connector, GmailConfig(True, GmailAccessMode.READ_ONLY)))

    response = _service(tmp_path, api).dispatch(
        "GET",
        "/v1/integrations/gmail/messages?q=is%3Aunread&limit=5",
    )

    assert response.status == 200
    assert response.body["items"][0]["snippet"] == "Preciso do seu retorno hoje."


def test_mobile_gmail_preview_does_not_send(tmp_path) -> None:
    connector = FakeGmailConnector()
    api = GmailAPI(
        GmailService(connector, GmailConfig(True, GmailAccessMode.DRAFT_AND_SEND))
    )
    response = _service(tmp_path, api).dispatch(
        "POST",
        "/v1/integrations/gmail/drafts/preview",
        {"recipients": ["jr@example.com"], "subject": "Olá", "body": "Mensagem"},
    )

    assert response.status == 200
    assert response.body["preview"]["external_action_performed"] is False
    assert connector.sent == []


def test_mobile_gmail_does_not_expose_send_route(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "POST",
        "/v1/integrations/gmail/messages/send",
        {"recipients": ["jr@example.com"], "subject": "Não enviar", "body": "Mensagem"},
    )
    assert response.status == 404


def test_dashboard_exposes_gmail_review_without_persistence() -> None:
    assert "Triagem opcional e prévia local" in DASHBOARD_HTML
    assert 'id="gmail-payload"' in DASHBOARD_HTML
    assert 'data-action="gmailUnread"' in DASHBOARD_HTML
    assert 'data-action="gmailPreview"' in DASHBOARD_HTML
    assert "localStorage" not in DASHBOARD_HTML
    assert "sessionStorage" not in DASHBOARD_HTML
