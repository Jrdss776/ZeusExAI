"""Orquestrador central de comandos do ZeusExAI.

A classificação é local e determinística. Nenhuma ação externa é executada sem um
handler explicitamente registrado pela aplicação hospedeira.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping


class CommandDomain(str, Enum):
    """Domínios suportados pelo orquestrador central."""

    ASSISTANT = "assistant"
    COMMERCIAL_ANALYSIS = "commercial_analysis"
    CAMPAIGN = "campaign"
    ACHADINHOS = "achadinhos"
    AGENDA = "agenda"
    DASHBOARD = "dashboard"
    DEVELOPMENT = "development"


@dataclass(frozen=True, slots=True)
class CommandDecision:
    """Resultado explicável da classificação de um comando."""

    domain: CommandDomain
    confidence: float
    matched_terms: tuple[str, ...]
    requires_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.value,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "requires_confirmation": self.requires_confirmation,
        }


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Resultado do despacho de um comando."""

    decision: CommandDecision
    handled: bool
    output: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.to_dict(),
            "handled": self.handled,
            "output": self.output,
        }


CommandHandler = Callable[[str, Mapping[str, Any]], Any]


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    ascii_text = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


_DOMAIN_TERMS: dict[CommandDomain, tuple[str, ...]] = {
    CommandDomain.ACHADINHOS: (
        "achadinhos",
        "achadinhos do jr",
        "produtos aprovados",
        "selecionar produtos",
    ),
    CommandDomain.COMMERCIAL_ANALYSIS: (
        "analise 360",
        "analisar produto",
        "analise comercial",
        "lucro",
        "margem",
        "roi",
        "concorrente",
        "precificacao",
        "preco recomendado",
    ),
    CommandDomain.CAMPAIGN: (
        "criar campanha",
        "gerar campanha",
        "anuncio",
        "copy",
        "descricao de produto",
        "titulo de produto",
    ),
    CommandDomain.AGENDA: (
        "agenda",
        "compromisso",
        "lembrete",
        "organize meu dia",
        "organizar meu dia",
        "tarefas de hoje",
    ),
    CommandDomain.DASHBOARD: (
        "dashboard",
        "painel",
        "abrir painel",
        "painel comercial",
    ),
    CommandDomain.DEVELOPMENT: (
        "codigo",
        "programar",
        "desenvolvimento",
        "corrigir bug",
        "teste automatizado",
        "github",
    ),
}

_SENSITIVE_TERMS = (
    "publicar",
    "enviar",
    "comprar",
    "excluir",
    "apagar",
    "executar",
)


class CommandOrchestrator:
    """Classifica e despacha comandos para handlers registrados."""

    def __init__(
        self,
        handlers: Mapping[CommandDomain | str, CommandHandler] | None = None,
    ) -> None:
        self._handlers: dict[CommandDomain, CommandHandler] = {}
        for domain, handler in (handlers or {}).items():
            self.register(domain, handler)

    def register(
        self,
        domain: CommandDomain | str,
        handler: CommandHandler,
    ) -> None:
        if not callable(handler):
            raise TypeError("handler precisa ser chamável.")
        self._handlers[CommandDomain(domain)] = handler

    def route(self, command: str) -> CommandDecision:
        normalized = _normalize(command)
        if not normalized:
            return CommandDecision(CommandDomain.ASSISTANT, 0.0, ())

        best_domain = CommandDomain.ASSISTANT
        best_matches: tuple[str, ...] = ()
        best_score = 0

        for domain, terms in _DOMAIN_TERMS.items():
            matches = tuple(term for term in terms if _normalize(term) in normalized)
            score = sum(len(_normalize(term).split()) for term in matches)
            if score > best_score:
                best_domain = domain
                best_matches = matches
                best_score = score

        requires_confirmation = any(
            _normalize(term) in normalized for term in _SENSITIVE_TERMS
        )
        confidence = (
            0.25
            if best_domain is CommandDomain.ASSISTANT
            else min(0.99, 0.55 + (0.08 * best_score))
        )

        return CommandDecision(
            domain=best_domain,
            confidence=round(confidence, 2),
            matched_terms=best_matches,
            requires_confirmation=requires_confirmation,
        )

    def dispatch(
        self,
        command: str,
        context: Mapping[str, Any] | None = None,
    ) -> CommandResult:
        decision = self.route(command)
        handler = self._handlers.get(decision.domain)
        if handler is None:
            return CommandResult(decision=decision, handled=False)
        output = handler(command, dict(context or {}))
        return CommandResult(decision=decision, handled=True, output=output)


__all__ = [
    "CommandDecision",
    "CommandDomain",
    "CommandHandler",
    "CommandOrchestrator",
    "CommandResult",
]
