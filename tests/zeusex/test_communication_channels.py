import pytest

from openjarvis.zeusex.communication_api import CommunicationAPI
from openjarvis.zeusex.communication_channels import (
    ChannelStatus,
    CommunicationAccessMode,
    CommunicationChannel,
    CommunicationService,
    DeliveryReceipt,
)


class FakeConnector:
    def __init__(self, channel: str, *, enabled: bool = True, authenticated: bool = True) -> None:
        self.channel = channel
        self.enabled = enabled
        self.authenticated = authenticated
        self.sent = []

    def status(self):
        return ChannelStatus(self.channel, self.enabled, self.authenticated, "indisponível")

    def send(self, preview):
        self.sent.append(preview)
        return DeliveryReceipt(self.channel, preview.recipient, "external-1", "sent")


def test_service_is_disabled_for_external_delivery_by_default() -> None:
    connector = FakeConnector("whatsapp")
    service = CommunicationService({CommunicationChannel.WHATSAPP: connector})
    preview = service.preview("whatsapp", "+5511999999999", "Olá")

    assert preview.external_action_performed is False
    assert preview.requires_confirmation is True
    with pytest.raises(PermissionError, match="desativados"):
        service.send(preview, confirmed=True)
    assert connector.sent == []


def test_local_notification_can_be_delivered_without_external_connector() -> None:
    service = CommunicationService({}, mode=CommunicationAccessMode.PREVIEW_ONLY)
    preview = service.preview("local", "device", "Lembrete local", title="ZeusExAI")
    receipt = service.send(preview)

    assert receipt.channel == "local"
    assert receipt.status == "delivered"


def test_preview_only_blocks_external_delivery() -> None:
    connector = FakeConnector("telegram")
    service = CommunicationService(
        {CommunicationChannel.TELEGRAM: connector},
        mode=CommunicationAccessMode.PREVIEW_ONLY,
    )
    preview = service.preview("telegram", "chat-1", "Mensagem")

    with pytest.raises(PermissionError, match="send_confirmed"):
        service.send(preview, confirmed=True)


def test_external_delivery_requires_explicit_confirmation() -> None:
    connector = FakeConnector("slack")
    service = CommunicationService(
        {CommunicationChannel.SLACK: connector},
        mode=CommunicationAccessMode.SEND_CONFIRMED,
    )
    preview = service.preview("slack", "#operacoes", "Alerta")

    with pytest.raises(PermissionError, match="confirmação explícita"):
        service.send(preview)
    receipt = service.send(preview, confirmed=True)

    assert receipt.external_id == "external-1"
    assert len(connector.sent) == 1


def test_unavailable_connector_blocks_delivery() -> None:
    connector = FakeConnector("whatsapp", authenticated=False)
    service = CommunicationService(
        {CommunicationChannel.WHATSAPP: connector},
        mode=CommunicationAccessMode.SEND_CONFIRMED,
    )
    preview = service.preview("whatsapp", "+5511999999999", "Olá")

    with pytest.raises(PermissionError, match="indisponível"):
        service.send(preview, confirmed=True)


def test_api_preview_never_sends() -> None:
    connector = FakeConnector("whatsapp")
    api = CommunicationAPI(
        CommunicationService(
            {CommunicationChannel.WHATSAPP: connector},
            mode=CommunicationAccessMode.SEND_CONFIRMED,
        )
    )
    response = api.dispatch(
        "POST",
        "/v1/integrations/communications/preview",
        {"channel": "whatsapp", "recipient": "+5511999999999", "body": "Olá"},
    )

    assert response.status == 200
    assert response.body["preview"]["external_action_performed"] is False
    assert connector.sent == []


def test_api_send_is_blocked_without_confirmation() -> None:
    connector = FakeConnector("telegram")
    api = CommunicationAPI(
        CommunicationService(
            {CommunicationChannel.TELEGRAM: connector},
            mode=CommunicationAccessMode.SEND_CONFIRMED,
        )
    )
    payload = {"channel": "telegram", "recipient": "chat-1", "body": "Olá"}

    blocked = api.dispatch("POST", "/v1/integrations/communications/send", payload)
    sent = api.dispatch(
        "POST",
        "/v1/integrations/communications/send",
        payload,
        confirmed=True,
    )

    assert blocked.status == 403
    assert sent.status == 201


def test_broadcast_requires_confirmation_for_all_external_items() -> None:
    whatsapp = FakeConnector("whatsapp")
    telegram = FakeConnector("telegram")
    service = CommunicationService(
        {
            CommunicationChannel.WHATSAPP: whatsapp,
            CommunicationChannel.TELEGRAM: telegram,
        },
        mode=CommunicationAccessMode.SEND_CONFIRMED,
    )
    previews = (
        service.preview("whatsapp", "+5511999999999", "Mensagem 1"),
        service.preview("telegram", "chat-1", "Mensagem 2"),
    )

    receipts = service.broadcast(previews, confirmed=True)

    assert len(receipts) == 2
    assert len(whatsapp.sent) == 1
    assert len(telegram.sent) == 1


def test_invalid_channel_and_empty_body_are_rejected() -> None:
    service = CommunicationService({})
    with pytest.raises(ValueError):
        service.preview("email", "destino", "Mensagem")
    with pytest.raises(ValueError, match="não pode ficar vazia"):
        service.preview("local", "device", "   ")
