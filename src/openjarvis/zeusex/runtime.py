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
from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.skills import SkillRegistry, default_registry


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
    memory_context_limit: int = 5

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        data_dir = Path(os.getenv("ZEUSEX_DATA_DIR", ".zeusex")).expanduser()
        history_limit = max(2, int(os.getenv("ZEUSEX_HISTORY_LIMIT", "12")))
        memory_context_limit = max(1, int(os.getenv("ZEUSEX_MEMORY_CONTEXT_LIMIT", "5")))
        return cls(
            data_dir=data_dir,
            history_limit=history_limit,
            memory_context_limit=memory_context_limit,
        )


class ZeusRuntime:
    """Processa comandos, Skills, memória e conversas com o motor de IA."""

    def __init__(
        self,
        engine: AIEngine | None = None,
        config: RuntimeConfig | None = None,
        skills: SkillRegistry | None = None,
    ) -> None:
        self.config = config or RuntimeConfig.from_env()
        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self.database_path = self.config.data_dir / "zeusex.db"
        self.engine = engine or DisabledEngine()
        self.skills = skills or default_registry()
        self._initialize_database()
        self.intelligent_memory = IntelligentMemoryStore(self.database_path)

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
        """Mantém o comando legado de memória sem alterar seu comportamento."""
        clean_content = content.strip()
        if not clean_content:
            return "Informe o que devo lembrar."
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO memories(content, created_at) VALUES (?, ?, ?)",
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

    def _remember_intelligent(self, argument: str) -> str:
        """Registra `categoria|projeto|importância|conteúdo`."""
        parts = [part.strip() for part in argument.split("|", 3)]
        if len(parts) != 4:
            return (
                "Use: lembrar-inteligente categoria|projeto|importância|conteúdo. "
                "Use '-' quando não houver projeto."
            )
        category, project, importance_text, content = parts
        try:
            importance = int(importance_text)
            memory = self.intelligent_memory.remember(
                content,
                category=category,
                project=None if project == "-" else project,
                importance=importance,
            )
        except ValueError as exc:
            return str(exc)
        return (
            f"Memória inteligente #{memory.id} registrada em {memory.category} "
            f"com importância {memory.importance}."
        )

    def _list_intelligent(self, argument: str) -> str:
        category = argument.strip() or None
        try:
            items = self.intelligent_memory.list(category=category, limit=10)
        except ValueError as exc:
            return str(exc)
        if not items:
            return "Nenhuma memória inteligente encontrada."
        rendered = [
            f"#{item.id} [{item.category}] {item.content}"
            + (f" (projeto: {item.project})" if item.project else "")
            for item in items
        ]
        return "Memórias inteligentes: " + " | ".join(rendered)

    def _search_intelligent(self, argument: str) -> str:
        items = self.intelligent_memory.search(argument, limit=10)
        if not items:
            return "Nenhuma memória inteligente encontrada."
        return "Resultados: " + " | ".join(
            f"#{item.id} [{item.category}] {item.content}" for item in items
        )

    def _memory_context(self, query: str) -> str:
        memories = self.intelligent_memory.search(
            query,
            limit=self.config.memory_context_limit,
        )
        if not memories:
            memories = self.intelligent_memory.list(limit=self.config.memory_context_limit)
        if not memories:
            return ""
        lines = [
            f"- [{item.category}] {item.content}"
            + (f" (projeto: {item.project})" if item.project else "")
            for item in memories
        ]
        return "\n\nMemórias locais relevantes:\n" + "\n".join(lines)

    def _handle_skill_command(self, argument: str, *, confirmed: bool = False) -> str:
        name, _, skill_argument = argument.strip().partition(" ")
        if not name:
            names = ", ".join(skill.name for skill in self.skills.list())
            return f"Skills disponíveis: {names}" if names else "Nenhuma Skill disponível."
        return self.skills.execute(name, skill_argument, confirmed=confirmed)

    def _generate_safely(self, prompt: str, history: list[tuple[str, str]]) -> str:
        try:
            response = self.engine.generate(prompt, history).strip()
        except Exception as exc:
            return (
                "Não consegui acessar o motor de IA. "
                f"Falha técnica: {type(exc).__name__}. Execute 'diagnose' para verificar a configuração."
            )
        return response or "O motor de IA não retornou uma resposta."

    def handle(self, text: str, mode: str = "assistant") -> str:
        clean_text = text.strip()
        if not clean_text:
            return "Diga ou digite uma mensagem."

        command, _, argument = clean_text.partition(" ")
        normalized_command = command.lower()
        if normalized_command == "status":
            return (
                f"{ZEUSEX_IDENTITY.name} online. Idioma: {ZEUSEX_IDENTITY.locale}. "
                f"Modo: {mode}. Palavra de ativação: {ZEUSEX_IDENTITY.wake_word}. "
                f"Skills: {len(self.skills.list())}."
            )
        if normalized_command == "ajuda":
            return (
                "Comandos: status, ajuda, lembrar <texto>, memoria, "
                "lembrar-inteligente categoria|projeto|importância|conteúdo, "
                "memoria-inteligente [categoria], buscar-memoria <consulta>, "
                "skill <nome> <argumento>, confirmar-skill <nome> <argumento>."
            )
        if normalized_command == "lembrar":
            return self.remember(argument)
        if normalized_command in {"memoria", "memória"}:
            items = self.memories()
            return "Memórias: " + " | ".join(items) if items else "Nenhuma memória registrada."
        if normalized_command in {"lembrar-inteligente", "lembrar_inteligente"}:
            return self._remember_intelligent(argument)
        if normalized_command in {"memoria-inteligente", "memória-inteligente"}:
            return self._list_intelligent(argument)
        if normalized_command in {"buscar-memoria", "buscar-memória"}:
            return self._search_intelligent(argument)
        if normalized_command == "skill":
            return self._handle_skill_command(argument)
        if normalized_command in {"confirmar-skill", "confirmar_skill"}:
            return self._handle_skill_command(argument, confirmed=True)

        history = self.recent_history()
        self._store_message("user", clean_text)
        system_prompt = ZEUSEX_IDENTITY.system_prompt(mode)
        memory_context = self._memory_context(clean_text)
        response = self._generate_safely(
            f"{system_prompt}{memory_context}\n\nUsuário: {clean_text}",
            history,
        )
        self._store_message("assistant", response)
        return response


__all__ = [
    "AIEngine",
    "CallableEngine",
    "DisabledEngine",
    "RuntimeConfig",
    "ZeusRuntime",
]
