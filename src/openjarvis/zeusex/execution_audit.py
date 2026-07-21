"""Trilha de auditoria local para decisões do executor ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sqlite3


@dataclass(frozen=True, slots=True)
class ExecutionAuditEvent:
    id: int
    queue_id: int
    action: str
    event: str
    decision: str
    reason: str
    duration_ms: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionAuditStore:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    event TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_audit_queue ON execution_audit_events(queue_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_execution_audit_action_time ON execution_audit_events(action, created_at)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _row(row: sqlite3.Row) -> ExecutionAuditEvent:
        return ExecutionAuditEvent(
            int(row["id"]), int(row["queue_id"]), str(row["action"]),
            str(row["event"]), str(row["decision"]), str(row["reason"]),
            int(row["duration_ms"]), str(row["created_at"]),
        )

    def record(
        self, queue_id: int, action: str, event: str, decision: str, reason: str,
        *, duration_ms: int = 0,
    ) -> ExecutionAuditEvent:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO execution_audit_events(queue_id, action, event, decision, reason, duration_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (queue_id, action, event, decision, reason, duration_ms, created_at),
            )
            event_id = int(cursor.lastrowid)
        return ExecutionAuditEvent(event_id, queue_id, action, event, decision, reason, duration_ms, created_at)

    def count(self, *, queue_id: int | None = None, action: str | None = None, event: str | None = None, since: str | None = None) -> int:
        clauses: list[str] = []
        values: list[object] = []
        for column, value in (("queue_id", queue_id), ("action", action), ("event", event)):
            if value is not None:
                clauses.append(f"{column} = ?")
                values.append(value)
        if since is not None:
            clauses.append("created_at >= ?")
            values.append(since)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            row = connection.execute(f"SELECT COUNT(*) AS total FROM execution_audit_events{where}", values).fetchone()
        return int(row["total"])

    def list(self, *, queue_id: int | None = None, action: str | None = None, limit: int = 100) -> list[ExecutionAuditEvent]:
        bounded = max(1, min(limit, 500))
        clauses: list[str] = []
        values: list[object] = []
        if queue_id is not None:
            clauses.append("queue_id = ?")
            values.append(queue_id)
        if action is not None:
            clauses.append("action = ?")
            values.append(action.strip().lower())
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(bounded)
        with self._connect() as connection:
            rows = connection.execute(f"SELECT * FROM execution_audit_events{where} ORDER BY id DESC LIMIT ?", values).fetchall()
        return [self._row(row) for row in rows]


__all__ = ["ExecutionAuditEvent", "ExecutionAuditStore"]
