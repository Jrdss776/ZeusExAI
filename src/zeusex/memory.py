"""Memória persistente em SQLite para o ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


@dataclass(frozen=True, slots=True)
class MemoryItem:
    role: str
    content: str
    created_at: str


class SQLiteMemory:
    """Armazena e recupera mensagens de conversa localmente."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add(self, role: str, content: str) -> None:
        clean_role = role.strip().lower()
        clean_content = content.strip()
        if not clean_role or not clean_content:
            raise ValueError("role e content não podem ser vazios")

        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO memories (role, content, created_at) VALUES (?, ?, ?)",
                (clean_role, clean_content, created_at),
            )

    def recent(self, limit: int = 20) -> list[MemoryItem]:
        safe_limit = max(1, min(limit, 200))
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content, created_at
                FROM memories
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

        return [
            MemoryItem(row["role"], row["content"], row["created_at"])
            for row in reversed(rows)
        ]
