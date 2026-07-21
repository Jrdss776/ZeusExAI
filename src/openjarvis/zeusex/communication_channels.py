"""Canais opcionais e seguros de comunicação do ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol, Sequence


class CommunicationAccessMode(str, Enum):
    DISABLED = "disabled"
    PREVIEW_ONLY = "preview_only"
    SEND_CONFIRMED = "send_confirmed"


class CommunicationChannel(str, Enum):
    LOCAL = "local"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    SLACK = "slack"


@dataclass(frozen=True, slots=True)
class ChannelStatus:
    channel: str
    enabled: bool
    authenticated: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NotificationPreview:
    channel: str
    recipient: str
    title: str
    body: str
    metadata: dict[str, str]
    requires_confirmation: bool
    external_action_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DeliveryReceipt:
    channel: str
    recipient: str
    external_id: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CommunicationConnector(Protocol):
    def status(self) -> ChannelStatus: ...

    def send(self, preview: NotificationPreview) -> DeliveryReceipt: ...


@dataclass(slots=True)
class DisabledCommunicationConnector:
    channel: CommunicationChannel
    reason: str = "Canal não configurado."

    def status(self) -> ChannelStatus:
        return ChannelStatus(self.channel.value, False, False, self.reason)

    def send(self, preview: NotificationPreview) -> DeliveryReceipt:
        del preview
        raise PermissionError(self.reason)


@dataclass(slots=True)
class CommunicationService:
    connectors: dict[CommunicationChannel, CommunicationConnector]
    mode: CommunicationAccessMode = CommunicationAccessMode.DISABLED
    max_body_length: int = 4000

    def __post_init__(self) -> None:
        if not 1 <= self.max_body_length <= 100_000:
            raise ValueError("max_body_length precisa estar entre 1 e 100000.")

    def statuses(self) -> tuple[ChannelStatus, ...]:
        return tuple(
            self.connectors.get(channel, DisabledCommunicationConnector(channel)).status()
            for channel in CommunicationChannel
        )

    def preview(
        self,
        channel: CommunicationChannel | str,
        recipient: str,
        body: str,
        *,
        title: str = "",
        metadata: dict[str, str] | None = None,
    ) -> NotificationPreview:
        normalized_channel = CommunicationChannel(channel)
        clean_recipient = recipient.strip()
        clean_body = body.strip()
        clean_title = title.strip()
        if not clean_recipient:
            raise ValueError("O destinatário não pode ficar vazio.")
        if not clean_body:
            raise ValueError("A mensagem não pode ficar vazia.")
        if len(clean_body) > self.max_body_length:
            raise ValueError("A mensagem excede o limite permitido.")
        if len(clean_title) > 200:
            raise ValueError("O título não pode exceder 200 caracteres.")
        safe_metadata = {str(key): str(value) for key, value in (metadata or {}).items()}
        return NotificationPreview(
            normalized_channel.value,
            clean_recipient,
            clean_title,
            clean_body,
            safe_metadata,
            requires_confirmation=normalized_channel is not CommunicationChannel.LOCAL,
        )

    def send(self, preview: NotificationPreview, *, confirmed: bool = False) -> DeliveryReceipt:
        channel = CommunicationChannel(preview.channel)
        if self.mode is CommunicationAccessMode.DISABLED:
            raise PermissionError("Canais de comunicação estão desativados.")
        if channel is CommunicationChannel.LOCAL:
            return DeliveryReceipt(channel.value, preview.recipient, "local", "delivered")
        if self.mode is not CommunicationAccessMode.SEND_CONFIRMED:
            raise PermissionError("Envio externo exige modo send_confirmed.")
        if not confirmed:
            raise PermissionError("Envio externo exige confirmação explícita.")
        connector = self.connectors.get(channel)
        if connector is None:
            raise PermissionError(f"Canal {channel.value} não configurado.")
        status = connector.status()
        if not status.enabled or not status.authenticated:
            raise PermissionError(status.reason or f"Canal {channel.value} indisponível.")
        return connector.send(preview)

    def broadcast(
        self,
        previews: Sequence[NotificationPreview],
        *,
        confirmed: bool = False,
    ) -> tuple[DeliveryReceipt, ...]:
        return tuple(self.send(preview, confirmed=confirmed) for preview in previews)


__all__ = [
    "ChannelStatus",
    "CommunicationAccessMode",
    "CommunicationChannel",
    "CommunicationConnector",
    "CommunicationService",
    "DeliveryReceipt",
    "DisabledCommunicationConnector",
    "NotificationPreview",
]
