"""Agendamento local seguro para tarefas declaradas do ZeusEXai."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import json
import sqlite3

ALLOWED_JOB_TYPES = frozenset({"analysis360", "campaign", "marketplace_queue"})
SCHEDULE_STATUSES = frozenset({"pending", "running", "completed", "failed"})


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    id: int
    job_type: str
    payload: dict[str, Any]
    scheduled_for: str
    status: str
    attempts: int
    error: str | None


class SafeScheduler:
    """Armazena tarefas permitidas; não cria threads nem executa shell."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
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
                CREATE TABLE IF NOT EXISTS safe_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT
                )
                """
            )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("O agendamento precisa incluir fuso horário.")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _serialize(payload: Mapping[str, Any]) -> str:
        try:
            return json.dumps(dict(payload), ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("O payload precisa ser compatível com JSON.") from exc

    @staticmethod
    def _row(row: sqlite3.Row) -> ScheduledTask:
        return ScheduledTask(
            id=row["id"],
            job_type=row["job_type"],
            payload=json.loads(row["payload"]),
            scheduled_for=row["scheduled_for"],
            status=row["status"],
            attempts=row["attempts"],
            error=row["error"],
        )

    def schedule(
        self,
        job_type: str,
        payload: Mapping[str, Any],
        scheduled_for: datetime,
    ) -> ScheduledTask:
        normalized_type = job_type.strip().lower()
        if normalized_type not in ALLOWED_JOB_TYPES:
            raise ValueError(f"Tipo de tarefa não permitido: {normalized_type}.")
        serialized = self._serialize(payload)
        when = self._utc(scheduled_for).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO safe_schedules(
                    job_type, payload, scheduled_for, status, attempts, error
                ) VALUES (?, ?, ?, 'pending', 0, NULL)
                """,
                (normalized_type, serialized, when),
            )
            row = connection.execute(
                "SELECT * FROM safe_schedules WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row(row)

    def list(self, *, status: str | None = None, limit: int = 100) -> list[ScheduledTask]:
        if status is not None and status not in SCHEDULE_STATUSES:
            raise ValueError("Status de agendamento inválido.")
        query = "SELECT * FROM safe_schedules"
        parameters: list[object] = []
        if status is not None:
            query += " WHERE status = ?"
            parameters.append(status)
        query += " ORDER BY scheduled_for ASC, id ASC LIMIT ?"
        parameters.append(max(1, min(limit, 1000)))
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._row(row) for row in rows]

    def claim_due(self, *, now: datetime | None = None) -> ScheduledTask | None:
        current = self._utc(now or datetime.now(timezone.utc)).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM safe_schedules
                WHERE status = 'pending' AND scheduled_for <= ?
                ORDER BY scheduled_for ASC, id ASC LIMIT 1
                """,
                (current,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE safe_schedules
                SET status = 'running', attempts = attempts + 1
                WHERE id = ? AND status = 'pending'
                """,
                (row["id"],),
            )
            updated = connection.execute(
                "SELECT * FROM safe_schedules WHERE id = ?",
                (row["id"],),
            ).fetchone()
        return self._row(updated)

    def finish(
        self,
        task_id: int,
        *,
        success: bool,
        error: str | None = None,
    ) -> ScheduledTask:
        status = "completed" if success else "failed"
        safe_error = None if success else (error or "Falha não especificada.").strip()[:500]
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE safe_schedules SET status = ?, error = ? WHERE id = ?",
                (status, safe_error, task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Agendamento não encontrado: {task_id}.")
            row = connection.execute(
                "SELECT * FROM safe_schedules WHERE id = ?",
                (task_id,),
            ).fetchone()
        return self._row(row)


__all__ = [
    "ALLOWED_JOB_TYPES",
    "SCHEDULE_STATUSES",
    "SafeScheduler",
    "ScheduledTask",
]
