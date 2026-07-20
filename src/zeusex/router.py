"""Roteamento simples e extensível de comandos."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

CommandHandler = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class RouteResult:
    command: str
    response: str


class CommandRouter:
    """Registra comandos e direciona mensagens para o manipulador correto."""

    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command: str, handler: CommandHandler) -> None:
        normalized = command.strip().lower()
        if not normalized:
            raise ValueError("command não pode ser vazio")
        self._handlers[normalized] = handler

    def dispatch(self, text: str) -> RouteResult | None:
        normalized = text.strip()
        if not normalized:
            return None

        command, _, argument = normalized.partition(" ")
        handler = self._handlers.get(command.lower())
        if handler is None:
            return None

        return RouteResult(command=command.lower(), response=handler(argument.strip()))

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))
