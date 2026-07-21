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
        messages = [
            GmailMessage(
                "1",
                "t1",
                "loja@example.com",
                ("jr@example.com",),
                "Pedido urgente",
                "Preciso do seu retorno hoje.",
                "2026-07-21T12:00:00Z",
                True,
            ),
            GmailMessage(
                "2",
                "t2",
                "news@example.com",
                ("jr@example.com",),
                "Novidades",
                "Confira as novidades da semana.",
                "2026-07-21T13:00:00Z",
                False,
            ),
        ]
        return messages[:max_results]

    def send_message(self, preview):
        self.sent.append(preview)
        return GmailMessage("sent-1", "t3", "jr@example.com", preview.recipients, preview.subject)


def test_gmail_is_disabled_by_default() -> None:
    service = GmailService()
    assert service.status().enabled is False
    with pytest.raises(PermissionError):
        service.list_messages()


def test_read_only_lists_and_blocks_send() -> None:
    service = GmailService(FakeGmailConnector(), GmailConfig(True, GmailAccessMode.READ_ONLY))
    assert service.list_messages(query="is:unread", limit=10)[0].subject == "Pedido urgente"
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


def test_summary_is_local_and_bounded() -> None:
    message = GmailMessage("1", "t1", "a@example.com", ("b@example.com",), "Assunto", "x" * 400)
    summary = GmailService.summarize(message, max_length=80)
    assert summary.startswith("Assunto — ")
    assert summary.endswith("…")
    assert len(summary) <= 91


def test_triage_prioritizes_messages_that_need_reply() -> None:
    service = GmailService(FakeGmailConnector(), GmailConfig(True, GmailAccessMode.READ_ONLY))
    items = service.triage(service.list_messages())
    assert items[0].category == "urgent"
    assert items[0].requires_reply is True
    assert items[1].category == "fyi"


def test_api_returns_summaries_and_triage() -> None:
    api = GmailAPI(GmailService(FakeGmailConnector(), GmailConfig(True, GmailAccessMode.READ_ONLY)))
    messages = api.dispatch("GET", "/v1/integrations/gmail/messages", query={"q": "in:inbox"})
    triage = api.dispatch("GET", "/v1/integrations/gmail/triage", query={"q": "in:inbox"})

    assert messages.status == 200
    assert len(messages.body["summaries"]) == 2
    assert triage.status == 200
    assert triage.body["requires_reply"] == 1
    assert triage.body["items"][0]["category"] == "urgent"


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
