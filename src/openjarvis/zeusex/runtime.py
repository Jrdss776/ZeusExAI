"""Runtime persistente e interface de motores de IA do ZeusExAI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
import os
import sqlite3

from openjarvis.zeusex.identity import ZEUSEX_IDENTITY


class AIEngine(Protocol):
    """Contrato mínimo para conectar qualquer motor local ou em nuvem."""

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        """Gera uma resposta usando o prompt e o histórico recente."""


@dataclass(slots=True)
class DisabledEngine:
    """Motor seguro usado enquanto nenhum provedor estiver configurado."""

    reason: str = "Nenhum motor de IA foi configurado."

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        del history
        return (
            f"Recebi: {prompt}. {self.reason} "
            "Os comandos locais continuam disponíveis em 'ajuda'."
        )


@dataclass(slots=True)
class CallableEngine:
    """Adaptador simples para funções, útil em testes e integrações futuras."""

    callback: Callable[[str, list[tuple[str, str]]], str]

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        return self.callback(prompt, history)


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Configuração local do runtime ZeusExAI."""

    data_dir: Path
    history_limit: int = 12

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        data_dir = Path(os.getenv("ZEUSEX_DATA_DIR", ".zeusex")).expanduser()
        history_limit = max(2, int(os.getenv("ZEUSEX_HISTORY_LIMIT", "12")))
        return cls(data_dir=data_dir, history_limit=history_limit)


class ZeusRuntime:
    """Processa comandos, mantém memória e delega conversas ao motor de IA."""

    def __init__(
        self,
        engine: AIEngine | None = None,
        config: RuntimeConfig | None = None,
    ) -> None:
        self.config = config or RuntimeConfig.from_env()
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.config.data_dir / "zeusex.db"
        self.engine = engine or DisabledEngine()
        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _store_message(self, role: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages(role, content, created_at) VALUES (?, ?, ?)",
                (role, content, self._now()),
            )

    def recent_history(self) -> list[tuple[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content FROM messages
                ORDER BY id DESC LIMIT ?
                """,
                (self.config.history_limit,),
            ).fetchall()
        return [(row["role"], row["content"]) for row in reversed(rows)]

    def remember(self, content: str) -> str:
        clean_content = content.strip()
        if not clean_content:
            return "Informe o que devo lembrar."
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO memories(content, created_at) VALUES (?, ?)",
                (clean_content, self._now()),
            )
        return f"Memória registrada: {clean_content}"

    def memories(self, limit: int = 10) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT content FROM memories ORDER BY id DESC LIMIT ?",
                (max(1, limit),),
            ).fetchall()
        return [row["content"] for row in rows]

    def handle(self, text: str, mode: str = "assistant") -> str:
        clean_text = text.strip()
        if not clean_text:
            return "Diga ou digite uma mensagem."

        command, _, argument = clean_text.partition(" ")
        normalized_command = command.lower()
        if normalized_command == "status":
            return (
                f"{ZEUSEX_IDENTITY.name} online. Idioma: {ZEUSEX_IDENTITY.locale}. "
                f"Modo: {mode}. Palavra de ativação: {ZEUSEX_IDENTITY.wake_word}."
            )
        if normalized_command == "ajuda":
            return "Comandos: status, ajuda, lembrar <texto>, memoria."
        if normalized_command == "lembrar":
            return self.remember(argument)
        if normalized_command in {"memoria", "memória"}:
            items = self.memories()
            return "Memórias: " + " | ".join(items) if items else "Nenhuma memória registrada."

        history = self.recent_history()
        self._store_message("user", clean_text)
        system_prompt = ZEUSEX_IDENTITY.system_prompt(mode)
        response = self.engine.generate(
            f"{system_prompt}\n\nUsuário: {clean_text}",
            history,
        ).strip()
        if not response:
            response = "O motor de IA não retornou uma resposta."
        self._store_message("assistant", response)
        return response


__all__ = [
    "AIEngine",
    "CallableEngine",
    "DisabledEngine",
    "RuntimeConfig",
    "ZeusRuntime",
]
