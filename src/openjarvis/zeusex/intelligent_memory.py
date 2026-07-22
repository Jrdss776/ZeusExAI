"""Memória inteligente categorizada e persistente do ZeusExAI."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sqlite3


ALLOWED_MEMORY_CATEGORIES = frozenset(
    {"general", "profile", "project", "product", "campaign", "preference", "decision"}
)


@dataclass(frozen=True, slots=True)
class IntelligentMemory:
    id: int
    category: str
    content: str
    project: str | None
    importance: int
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class IntelligentMemoryStore:
    """Armazena memórias estruturadas sem substituir a memória legada."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS intelligent_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    project TEXT,
                    importance INTEGER NOT NULL DEFAULT 3,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_intelligent_memories_category "
                "ON intelligent_memories(category)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_intelligent_memories_project "
                "ON intelligent_memories(project)"
            )

    @staticmethod
    def _validate_category(category: str) -> str:
        normalized = category.strip().lower()
        if normalized not in ALLOWED_MEMORY_CATEGORIES:
            allowed = ", ".join(sorted(ALLOWED_MEMORY_CATEGORIES))
            raise ValueError(f"Categoria inválida. Use uma destas: {allowed}.")
        return normalized

    def remember(
        self,
        content: str,
        *,
        category: str = "general",
        project: str | None = None,
        importance: int = 3,
    ) -> IntelligentMemory:
        clean_content = content.strip()
        if not clean_content:
            raise ValueError("O conteúdo da memória não pode ficar vazio.")
        normalized_category = self._validate_category(category)
        if not 1 <= importance <= 5:
            raise ValueError("importance precisa estar entre 1 e 5.")
        clean_project = project.strip() if project and project.strip() else None
        now = self._now()
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO intelligent_memories(
                    category, content, project, importance, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (normalized_category, clean_content, clean_project, importance, now, now),
            )
            memory_id = int(cursor.lastrowid)
        return self.get(memory_id)

    def get(self, memory_id: int) -> IntelligentMemory:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM intelligent_memories WHERE id = ?", (memory_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Memória {memory_id} não encontrada.")
        return IntelligentMemory(**dict(row))

    def list(
        self,
        *,
        category: str | None = None,
        project: str | None = None,
        limit: int = 20,
    ) -> list[IntelligentMemory]:
        clauses: list[str] = []
        values: list[object] = []
        if category is not None:
            clauses.append("category = ?")
            values.append(self._validate_category(category))
        if project is not None:
            clauses.append("project = ?")
            values.append(project.strip())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(max(1, limit))
        with self._connection() as connection:
            rows = connection.execute(
                f"SELECT * FROM intelligent_memories{where} "
                "ORDER BY importance DESC, id DESC LIMIT ?",
                values,
            ).fetchall()
        return [IntelligentMemory(**dict(row)) for row in rows]

    def search(self, query: str, *, limit: int = 20) -> list[IntelligentMemory]:
        clean_query = query.strip()
        if not clean_query:
            return []
        pattern = f"%{clean_query}%"
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM intelligent_memories
                WHERE content LIKE ? OR project LIKE ?
                ORDER BY importance DESC, id DESC LIMIT ?
                """,
                (pattern, pattern, max(1, limit)),
            ).fetchall()
        return [IntelligentMemory(**dict(row)) for row in rows]


__all__ = [
    "ALLOWED_MEMORY_CATEGORIES",
    "IntelligentMemory",
    "IntelligentMemoryStore",
]
