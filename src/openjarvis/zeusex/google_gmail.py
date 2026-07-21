"""Integração opcional e segura com Gmail para o ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


ALLOWED_GMAIL_MODES = frozenset({"disabled", "read_only", "read_write"})


@dataclass(frozen=True, slots=True)
class GmailMessage:
    id: str
    thread_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    snippet: str
    received_at: str
    labels: tuple[str, ...] = ()
    unread: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GmailConnectorStatus:
    enabled: bool
    mode: str
    authenticated: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GmailSearchResult:
    messages: tuple[GmailMessage, ...]
    total: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "messages": [message.to_dict() for message in self.messages],
            "total": self.total,
        }


@dataclass(frozen=True, slots=True)
class GmailTriageItem:
    message: GmailMessage
    category: str
    reason: str
    requires_reply: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message.to_dict(),
            "category": self.category,
            "reason": self.reason,
            "requires_reply": self.requires_reply,
        }


class GmailConnector(Protocol):
    def status(self) -> GmailConnectorStatus: ...

    def search(self, query: str, *, limit: int = 20) -> GmailSearchResult: ...

    def get_message(self, message_id: str) -> GmailMessage: ...


@dataclass(slots=True)
class DisabledGmailConnector:
    reason: str = "Integração com Gmail não configurada."

    def status(self) -> GmailConnectorStatus:
        return GmailConnectorStatus(False, "disabled", False, self.reason)

    def search(self, query: str, *, limit: int = 20) -> GmailSearchResult:
        del query, limit
        raise PermissionError(self.reason)

    def get_message(self, message_id: str) -> GmailMessage:
        del message_id
        raise PermissionError(self.reason)


@dataclass(slots=True)
class GmailService:
    connector: GmailConnector
    mode: str = "disabled"

    def __post_init__(self) -> None:
        normalized = self.mode.strip().lower()
        if normalized not in ALLOWED_GMAIL_MODES:
            raise ValueError("Modo do Gmail inválido.")
        self.mode = normalized

    def status(self) -> GmailConnectorStatus:
        connector_status = self.connector.status()
        if self.mode == "disabled":
            return GmailConnectorStatus(False, "disabled", False, "Integração desativada.")
        return GmailConnectorStatus(
            connector_status.enabled,
            self.mode,
            connector_status.authenticated,
            connector_status.reason,
        )

    def _require_read(self) -> None:
        if self.mode == "disabled":
            raise PermissionError("Integração com Gmail desativada.")
        status = self.connector.status()
        if not status.enabled or not status.authenticated:
            raise PermissionError(status.reason or "Gmail não autenticado.")

    def search(self, query: str, *, limit: int = 20) -> GmailSearchResult:
        self._require_read()
        bounded = max(1, min(int(limit), 100))
        return self.connector.search(query.strip(), limit=bounded)

    def get_message(self, message_id: str) -> GmailMessage:
        self._require_read()
        clean_id = message_id.strip()
        if not clean_id:
            raise ValueError("message_id não pode ficar vazio.")
        return self.connector.get_message(clean_id)

    @staticmethod
    def summarize(message: GmailMessage, *, max_length: int = 240) -> str:
        text = message.snippet.strip()
        if not text:
            return f"{message.subject or '(sem assunto)'} — mensagem sem prévia disponível."
        limit = max(40, min(int(max_length), 1000))
        summary = text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
        return f"{message.subject or '(sem assunto)'} — {summary}"

    @staticmethod
    def triage(messages: tuple[GmailMessage, ...] | list[GmailMessage]) -> tuple[GmailTriageItem, ...]:
        urgent_terms = ("urgente", "prazo", "vencimento", "hoje", "amanhã", "acao necessaria", "ação necessária")
        reply_terms = ("responda", "retorno", "confirma", "pode enviar", "aguardo", "preciso de você")
        items: list[GmailTriageItem] = []
        for message in messages:
            haystack = f"{message.subject} {message.snippet}".casefold()
            urgent = any(term in haystack for term in urgent_terms)
            requires_reply = urgent or any(term in haystack for term in reply_terms)
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
            items.append(GmailTriageItem(message, category, reason, requires_reply))
        order = {"urgent": 0, "needs_reply": 1, "unread": 2, "fyi": 3}
        items.sort(key=lambda item: (order[item.category], item.message.received_at), reverse=False)
        return tuple(items)


__all__ = [
    "ALLOWED_GMAIL_MODES",
    "DisabledGmailConnector",
    "GmailConnector",
    "GmailConnectorStatus",
    "GmailMessage",
    "GmailSearchResult",
    "GmailService",
    "GmailTriageItem",
]
