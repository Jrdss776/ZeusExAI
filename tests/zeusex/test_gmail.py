import pytest

from openjarvis.zeusex.gmail import (
    GmailAccessMode,
    GmailConfig,
    GmailConnectorStatus,
    GmailMessage,
    GmailService,
)
from openjarvis.zeusex.gmail_api import GmailAPI


class FakeGmailConnector:
    def __init__(self) -> None:
        self.sent = []

    def status(self):
        return GmailConnectorStatus(True, "draft_and_send", True)

    def list_messages(self, *, query, max_results):
        return [GmailMessage("1", "t1", "loja@example.com", ("jr@example.com",), "Pedido", query or "")]

    def send_message(self, preview):
        self.sent.append(preview)
        return GmailMessage("sent-1", "t2", "jr@example.com", preview.recipients, preview.subject)


def test_gmail_is_disabled_by_default() -> None:
    service = GmailService()
    assert service.status().enabled is False
    with pytest.raises(PermissionError):
        service.list_messages()


def test_read_only_lists_and_blocks_send() -> None:
    service = GmailService(FakeGmailConnector(), GmailConfig(True, GmailAccessMode.READ_ONLY))
    assert service.list_messages(query="is:unread", limit=10)[0].subject == "Pedido"
    preview = service.preview_draft(["JR@Example.com"], "Resposta", "Mensagem")
    with pytest.raises(PermissionError):
        service.send(preview, confirmed=True)


def test_preview_is_local_and_send_requires_confirmation() -> None:
    connector = FakeGmailConnector()
    service = GmailService(connector, GmailConfig(True, GmailAccessMode.DRAFT_AND_SEND))
    preview = service.preview_draft(["JR@Example.com", "jr@example.com"], " Resposta ", " Corpo ")

    assert preview.recipients == ("jr@example.com",)
    assert preview.external_action_performed is False
    assert connector.sent == []
    with pytest.raises(PermissionError):
        service.send(preview)
    sent = service.send(preview, confirmed=True)
    assert sent.id == "sent-1"


def test_api_preview_never_sends_and_send_is_blocked_without_confirmation() -> None:
    connector = FakeGmailConnector()
    api = GmailAPI(GmailService(connector, GmailConfig(True, GmailAccessMode.DRAFT_AND_SEND)))
    payload = {"recipients": ["jr@example.com"], "subject": "Olá", "body": "Mensagem"}

    preview = api.dispatch("POST", "/v1/integrations/gmail/drafts/preview", payload)
    blocked = api.dispatch("POST", "/v1/integrations/gmail/messages/send", payload)

    assert preview.status == 200
    assert preview.body["preview"]["external_action_performed"] is False
    assert blocked.status == 403
    assert connector.sent == []


def test_invalid_recipient_is_rejected() -> None:
    with pytest.raises(ValueError, match="válido"):
        GmailService().preview_draft(["invalido"], "Assunto", "Corpo")
