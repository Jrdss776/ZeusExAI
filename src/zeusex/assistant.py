"""Orquestrador principal do ZeusExAI."""

from __future__ import annotations

from .config import ZeusConfig
from .logging import configure_logging
from .memory import SQLiteMemory
from .router import CommandRouter


class ZeusAssistant:
    """Une configuração, memória, logs e roteamento de comandos."""

    def __init__(self, config: ZeusConfig | None = None) -> None:
        self.config = config or ZeusConfig.from_env()
        self.config.ensure_directories()
        self.logger = configure_logging(
            self.config.data_dir / "logs", self.config.log_level
        )
        self.memory = SQLiteMemory(self.config.data_dir / "memory.db")
        self.router = CommandRouter()
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        self.router.register("status", self._status)
        self.router.register("ajuda", self._help)
        self.router.register("lembrar", self._remember)
        self.router.register("memoria", self._show_memory)

    def handle(self, text: str) -> str:
        clean_text = text.strip()
        if not clean_text:
            return "Diga ou digite um comando."

        self.memory.add("user", clean_text)
        routed = self.router.dispatch(clean_text)
        response = routed.response if routed else self._fallback(clean_text)
        self.memory.add("assistant", response)
        self.logger.info("Comando processado: %s", clean_text.split(maxsplit=1)[0])
        return response

    def _status(self, _: str) -> str:
        return (
            f"{self.config.name} online. Idioma: {self.config.language}. "
            f"Palavra de ativação: {self.config.wake_word}."
        )

    def _help(self, _: str) -> str:
        return "Comandos disponíveis: " + ", ".join(self.router.commands)

    def _remember(self, argument: str) -> str:
        if not argument:
            return "Informe o que devo lembrar. Exemplo: lembrar reunião às 15h"
        self.memory.add("memory", argument)
        return f"Memória registrada: {argument}"

    def _show_memory(self, _: str) -> str:
        items = [item.content for item in self.memory.recent(10) if item.role == "memory"]
        if not items:
            return "Ainda não há memórias registradas."
        return "Memórias recentes: " + " | ".join(items)

    def _fallback(self, text: str) -> str:
        return (
            f"Recebi: {text}. O módulo de IA ainda será conectado; "
            "use 'ajuda' para ver os comandos locais disponíveis."
        )
