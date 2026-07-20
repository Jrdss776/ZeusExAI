"""Fila SQLite persistente para análises comerciais em lote."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import json
import sqlite3

from openjarvis.zeusex.marketplace import SUPPORTED_MARKETPLACES

QUEUE_STATUSES = frozenset({"queued", "processing", "completed", "failed"})


@dataclass(frozen=True, slots=True)
class AnalysisJob:
    id: int
    marketplace: str
    payload: dict[str, Any]
    status: str
    attempts: int
    error: str | None
    result: dict[str, Any] | None = None


class AnalysisQueue:
    """Armazena trabalhos e resultados localmente para retomada segura."""

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
                CREATE TABLE IF NOT EXISTS marketplace_analysis_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marketplace TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    result TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(marketplace_analysis_queue)"
                ).fetchall()
            }
            if "result" not in columns:
                connection.execute(
                    "ALTER TABLE marketplace_analysis_queue ADD COLUMN result TEXT"
                )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _marketplace(value: str) -> str:
        normalized = value.strip().lower().replace(" ", "_")
        if normalized not in SUPPORTED_MARKETPLACES:
            raise ValueError("Marketplace suportado: shopee ou mercado_livre.")
        return normalized

    @staticmethod
    def _serialize(payload: Mapping[str, Any]) -> str:
        try:
            return json.dumps(dict(payload), ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("O payload precisa ser compatível com JSON.") from exc

    @staticmethod
    def _decode(value: str | None) -> dict[str, Any] | None:
        return json.loads(value) if value else None

    @classmethod
    def _row(cls, row: sqlite3.Row) -> AnalysisJob:
        return AnalysisJob(
            id=row["id"],
            marketplace=row["marketplace"],
            payload=json.loads(row["payload"]),
            status=row["status"],
            attempts=row["attempts"],
            error=row["error"],
            result=cls._decode(row["result"]),
        )

    def enqueue(self, marketplace: str, payload: Mapping[str, Any]) -> AnalysisJob:
        normalized = self._marketplace(marketplace)
        serialized = self._serialize(payload)
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO marketplace_analysis_queue(
                    marketplace, payload, status, attempts, error, result,
                    created_at, updated_at
                ) VALUES (?, ?, 'queued', 0, NULL, NULL, ?, ?)
                """,
                (normalized, serialized, now, now),
            )
            row = connection.execute(
                "SELECT * FROM marketplace_analysis_queue WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return self._row(row)

    def get(self, job_id: int) -> AnalysisJob | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM marketplace_analysis_queue WHERE id = ?",
                (job_id,),
            ).fetchone()
        return self._row(row) if row else None

    def list(self, *, status: str | None = None, limit: int = 100) -> list[AnalysisJob]:
        if status is not None and status not in QUEUE_STATUSES:
            raise ValueError("Status de fila inválido.")
        query = "SELECT * FROM marketplace_analysis_queue"
        parameters: list[object] = []
        if status:
            query += " WHERE status = ?"
            parameters.append(status)
        query += " ORDER BY id ASC LIMIT ?"
        parameters.append(max(1, min(limit, 1000)))
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._row(row) for row in rows]

    def claim_next(self) -> AnalysisJob | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM marketplace_analysis_queue
                WHERE status = 'queued'
                ORDER BY id ASC LIMIT 1
                """
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE marketplace_analysis_queue
                SET status = 'processing', attempts = attempts + 1, updated_at = ?
                WHERE id = ? AND status = 'queued'
                """,
                (self._now(), row["id"]),
            )
            updated = connection.execute(
                "SELECT * FROM marketplace_analysis_queue WHERE id = ?",
                (row["id"],),
            ).fetchone()
        return self._row(updated)

    def complete(
        self,
        job_id: int,
        result: Mapping[str, Any] | None = None,
    ) -> AnalysisJob:
        serialized = self._serialize(result) if result is not None else None
        return self._transition(job_id, "completed", None, serialized)

    def fail(
        self,
        job_id: int,
        error: str,
        *,
        retry: bool = True,
        max_attempts: int = 3,
    ) -> AnalysisJob:
        current = self.get(job_id)
        if current is None:
            raise KeyError(f"Trabalho não encontrado: {job_id}.")
        status = "queued" if retry and current.attempts < max(1, max_attempts) else "failed"
        safe_error = error.strip()[:500] or "Falha não especificada."
        return self._transition(job_id, status, safe_error, None)

    def _transition(
        self,
        job_id: int,
        status: str,
        error: str | None,
        result: str | None,
    ) -> AnalysisJob:
        if status not in QUEUE_STATUSES:
            raise ValueError("Status de fila inválido.")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE marketplace_analysis_queue
                SET status = ?, error = ?, result = COALESCE(?, result), updated_at = ?
                WHERE id = ?
                """,
                (status, error, result, self._now(), job_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Trabalho não encontrado: {job_id}.")
            row = connection.execute(
                "SELECT * FROM marketplace_analysis_queue WHERE id = ?",
                (job_id,),
            ).fetchone()
        return self._row(row)


__all__ = ["AnalysisJob", "AnalysisQueue", "QUEUE_STATUSES"]
