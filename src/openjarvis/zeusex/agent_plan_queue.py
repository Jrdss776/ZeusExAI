"""Fila local persistente para revisão de planos do Agent Runtime.

A Fase 17.2 adiciona persistência e ciclo de aprovação, mas não executa planos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import json
import sqlite3

from openjarvis.zeusex.agent_runtime import AgentPlan


class PlanQueueStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class QueuedAgentPlan:
    id: int
    plan_id: str
    command: str
    domain: str
    status: str
    requires_confirmation: bool
    payload: dict[str, Any]
    created_at: str
    expires_at: str
    reviewed_at: str | None
    review_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentPlanQueue:
    """Persiste planos localmente e controla transições de revisão."""

    def __init__(self, database_path: Path | str, *, default_ttl_minutes: int = 60) -> None:
        if not 1 <= default_ttl_minutes <= 43_200:
            raise ValueError("default_ttl_minutes precisa estar entre 1 e 43200.")
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.default_ttl_minutes = default_ttl_minutes
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_plan_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL UNIQUE,
                    command TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requires_confirmation INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    review_note TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_agent_plan_queue_status "
                "ON agent_plan_queue(status)"
            )

    @staticmethod
    def _row(row: sqlite3.Row) -> QueuedAgentPlan:
        return QueuedAgentPlan(
            id=int(row["id"]),
            plan_id=str(row["plan_id"]),
            command=str(row["command"]),
            domain=str(row["domain"]),
            status=str(row["status"]),
            requires_confirmation=bool(row["requires_confirmation"]),
            payload=json.loads(str(row["payload_json"])),
            created_at=str(row["created_at"]),
            expires_at=str(row["expires_at"]),
            reviewed_at=row["reviewed_at"],
            review_note=str(row["review_note"]),
        )

    def enqueue(self, plan: AgentPlan, *, ttl_minutes: int | None = None) -> QueuedAgentPlan:
        ttl = self.default_ttl_minutes if ttl_minutes is None else ttl_minutes
        if not 1 <= ttl <= 43_200:
            raise ValueError("ttl_minutes precisa estar entre 1 e 43200.")
        now = self._now()
        expires_at = now + timedelta(minutes=ttl)
        payload = plan.to_dict()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO agent_plan_queue(
                    plan_id, command, domain, status, requires_confirmation,
                    payload_json, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan.id,
                    plan.command,
                    plan.decision.domain.value,
                    PlanQueueStatus.PENDING.value,
                    int(plan.requires_confirmation),
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                    now.isoformat(),
                    expires_at.isoformat(),
                ),
            )
            queue_id = int(cursor.lastrowid)
        return self.get(queue_id)

    def get(self, queue_id: int) -> QueuedAgentPlan:
        self.expire_due()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM agent_plan_queue WHERE id = ?", (queue_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Plano enfileirado {queue_id} não encontrado.")
        return self._row(row)

    def list(self, *, status: PlanQueueStatus | str | None = None, limit: int = 50) -> list[QueuedAgentPlan]:
        self.expire_due()
        bounded = max(1, min(limit, 200))
        values: list[object] = []
        where = ""
        if status is not None:
            normalized = PlanQueueStatus(status).value
            where = " WHERE status = ?"
            values.append(normalized)
        values.append(bounded)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM agent_plan_queue{where} ORDER BY id DESC LIMIT ?",
                values,
            ).fetchall()
        return [self._row(row) for row in rows]

    def approve(self, queue_id: int, *, note: str = "") -> QueuedAgentPlan:
        return self._review(queue_id, PlanQueueStatus.APPROVED, note)

    def reject(self, queue_id: int, *, note: str = "") -> QueuedAgentPlan:
        return self._review(queue_id, PlanQueueStatus.REJECTED, note)

    def _review(self, queue_id: int, status: PlanQueueStatus, note: str) -> QueuedAgentPlan:
        current = self.get(queue_id)
        if current.status != PlanQueueStatus.PENDING.value:
            raise ValueError("Somente planos pendentes podem ser revisados.")
        now = self._now().isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE agent_plan_queue
                SET status = ?, reviewed_at = ?, review_note = ?
                WHERE id = ? AND status = ?
                """,
                (status.value, now, note.strip(), queue_id, PlanQueueStatus.PENDING.value),
            )
        return self.get(queue_id)

    def expire_due(self) -> int:
        now = self._now().isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE agent_plan_queue
                SET status = ?
                WHERE status = ? AND expires_at <= ?
                """,
                (PlanQueueStatus.EXPIRED.value, PlanQueueStatus.PENDING.value, now),
            )
            return int(cursor.rowcount)

    def execute(self, queue_id: int, *, confirmed: bool = False) -> None:
        del queue_id, confirmed
        raise PermissionError("A Fase 17.2 permite aprovação, mas não executa planos.")


__all__ = ["AgentPlanQueue", "PlanQueueStatus", "QueuedAgentPlan"]
