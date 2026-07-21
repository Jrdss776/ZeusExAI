"""Contratos opcionais e seguros para integração futura com Gmail."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol, Sequence
import re


class GmailAccessMode(str, Enum):
    DISABLED = "disabled"
    READ_ONLY = "read_only"
    DRAFT_AND_SEND = "draft_and_send"


@dataclass(frozen=True, slots=True)
class GmailConnectorStatus:
    enabled: bool
    access_mode: str
    authenticated: bool = False
    provider: str = "gmail"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GmailMessage:
    id: str
    thread_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    snippet: str = ""
    received_at: str = ""
    unread: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GmailTriageItem:
    message: GmailMessage
    category: str
    reason: str
    requires_reply: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message.to_dict(),
            "category": self.category,
            "reason": self.reason,
            "requires_reply": self.requires_reply,
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class GmailDraftPreview:
    recipients: tuple[str, ...]
    subject: str
    body: str
    requires_confirmation: bool = True
    external_action_performed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GmailConfig:
    enabled: bool = False
    access_mode: GmailAccessMode = GmailAccessMode.DISABLED
    max_results: int = 50

    def __post_init__(self) -> None:
        if self.enabled and self.access_mode is GmailAccessMode.DISABLED:
            raise ValueError("Gmail habilitado exige modo read_only ou draft_and_send.")
        if not 1 <= self.max_results <= 100:
            raise ValueError("max_results precisa estar entre 1 e 100.")


class GmailConnector(Protocol):
    def status(self) -> GmailConnectorStatus:
        """Retorna estado sanitizado, sem tokens."""

    def list_messages(self, *, query: str | None, max_results: int) -> Sequence[GmailMessage]:
        """Consulta mensagens sem alterar a caixa postal."""

    def send_message(self, preview: GmailDraftPreview) -> GmailMessage:
        """Envia somente após a política externa autorizar."""


class DisabledGmailConnector:
    def status(self) -> GmailConnectorStatus:
        return GmailConnectorStatus(
            enabled=False,
            access_mode=GmailAccessMode.DISABLED.value,
            reason="Gmail não configurado.",
        )

    def list_messages(self, **_: Any) -> Sequence[GmailMessage]:
        raise RuntimeError("Gmail não configurado.")

    def send_message(self, preview: GmailDraftPreview) -> GmailMessage:
        del preview
        raise RuntimeError("Gmail não configurado.")


class GmailService:
    """Aplica limites, triagem e confirmação sem conhecer OAuth ou SDK Google."""

    _EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    _URGENT_TERMS = (
        "urgente",
        "prazo",
        "vencimento",
        "hoje",
        "amanhã",
        "acao necessaria",
        "ação necessária",
    )
    _REPLY_TERMS = (
        "responda",
        "retorno",
        "confirma",
        "pode enviar",
        "aguardo",
        "preciso de você",
    )

    def __init__(
        self,
        connector: GmailConnector | None = None,
        config: GmailConfig | None = None,
    ) -> None:
        self.connector = connector or DisabledGmailConnector()
        self.config = config or GmailConfig()

    def status(self) -> GmailConnectorStatus:
        connector_status = self.connector.status()
        if not self.config.enabled:
            return GmailConnectorStatus(
                enabled=False,
                access_mode=GmailAccessMode.DISABLED.value,
                authenticated=connector_status.authenticated,
                reason="Integração desativada na configuração local.",
            )
        return connector_status

    def list_messages(self, *, query: str | None = None, limit: int | None = None) -> list[GmailMessage]:
        if not self.config.enabled:
            raise PermissionError("Integração com Gmail está desativada.")
        if self.config.access_mode not in {GmailAccessMode.READ_ONLY, GmailAccessMode.DRAFT_AND_SEND}:
            raise PermissionError("Leitura do Gmail não autorizada.")
        clean_query = query.strip() if query and query.strip() else None
        if clean_query and len(clean_query) > 500:
            raise ValueError("A consulta do Gmail não pode exceder 500 caracteres.")
        bounded = min(max(1, limit or self.config.max_results), self.config.max_results)
        return list(self.connector.list_messages(query=clean_query, max_results=bounded))[:bounded]

    @staticmethod
    def summarize(message: GmailMessage, *, max_length: int = 240) -> str:
        limit = max(40, min(int(max_length), 1000))
        snippet = message.snippet.strip()
        if not snippet:
            return f"{message.subject or '(sem assunto)'} — mensagem sem prévia disponível."
        text = snippet if len(snippet) <= limit else snippet[: limit - 1].rstrip() + "…"
        return f"{message.subject or '(sem assunto)'} — {text}"

    def triage(self, messages: Sequence[GmailMessage]) -> tuple[GmailTriageItem, ...]:
        items: list[GmailTriageItem] = []
        for message in messages:
            haystack = f"{message.subject} {message.snippet}".casefold()
            urgent = any(term in haystack for term in self._URGENT_TERMS)
            requires_reply = urgent or any(term in haystack for term in self._REPLY_TERMS)
            if urgent:
                category = "urgent"
                reason = "Contém termo de urgência ou prazo."
            elif requires_reply:
                category = "needs_reply"
                reason = "Indica solicitação de retorno ou confirmação."
            elif message.unread:
                category = "unread"
                reason = "Mensagem ainda não lida."
            else:
                category = "fyi"
                reason = "Sem sinal explícito de urgência ou resposta necessária."
            items.append(
                GmailTriageItem(
                    message=message,
                    category=category,
                    reason=reason,
                    requires_reply=requires_reply,
                    summary=self.summarize(message),
                )
            )
        order = {"urgent": 0, "needs_reply": 1, "unread": 2, "fyi": 3}
        items.sort(key=lambda item: (order[item.category], item.message.received_at))
        return tuple(items)

    def preview_draft(
        self,
        recipients: Sequence[str],
        subject: str,
        body: str,
    ) -> GmailDraftPreview:
        normalized = tuple(dict.fromkeys(address.strip().lower() for address in recipients))
        if not normalized or any(not self._EMAIL.fullmatch(address) for address in normalized):
            raise ValueError("Informe ao menos um destinatário de e-mail válido.")
        clean_subject = subject.strip()
        clean_body = body.strip()
        if not clean_subject or len(clean_subject) > 200:
            raise ValueError("O assunto precisa ter entre 1 e 200 caracteres.")
        if not clean_body or len(clean_body) > 100_000:
            raise ValueError("O corpo precisa ter entre 1 e 100000 caracteres.")
        return GmailDraftPreview(normalized, clean_subject, clean_body)

    def send(self, preview: GmailDraftPreview, *, confirmed: bool = False) -> GmailMessage:
        if not self.config.enabled:
            raise PermissionError("Integração com Gmail está desativada.")
        if self.config.access_mode is not GmailAccessMode.DRAFT_AND_SEND:
            raise PermissionError("Envio exige modo draft_and_send.")
        if not confirmed:
            raise PermissionError("Envio de e-mail exige confirmação explícita.")
        return self.connector.send_message(preview)


__all__ = [
    "DisabledGmailConnector",
    "GmailAccessMode",
    "GmailConfig",
    "GmailConnector",
    "GmailConnectorStatus",
    "GmailDraftPreview",
    "GmailMessage",
    "GmailService",
    "GmailTriageItem",
]
