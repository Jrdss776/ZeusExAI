"""Sistema persistente de objetivos mensuráveis do ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sqlite3


ALLOWED_GOAL_STATUSES = frozenset({"planned", "active", "paused", "achieved", "cancelled"})
ALLOWED_GOAL_DIRECTIONS = frozenset({"increase", "decrease", "maintain"})


@dataclass(frozen=True, slots=True)
class Goal:
    id: int
    project_id: int | None
    title: str
    description: str
    metric: str
    direction: str
    baseline: float
    target: float
    current: float
    unit: str
    status: str
    due_at: str | None
    created_at: str
    updated_at: str

    @property
    def progress_percent(self) -> float:
        if self.direction == "maintain":
            return 100.0 if self.current == self.target else 0.0
        span = self.target - self.baseline
        if span == 0:
            return 100.0 if self.current == self.target else 0.0
        progress = ((self.current - self.baseline) / span) * 100
        return round(max(0.0, min(100.0, progress)), 2)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["progress_percent"] = self.progress_percent
        return data


@dataclass(frozen=True, slots=True)
class GoalCheckIn:
    id: int
    goal_id: int
    value: float
    note: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GoalStore:
    """Mantém objetivos e medições em SQLite, sem executar ações externas."""

    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    metric TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    baseline REAL NOT NULL,
                    target REAL NOT NULL,
                    current REAL NOT NULL,
                    unit TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    due_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE RESTRICT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS goal_checkins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal_id INTEGER NOT NULL,
                    value REAL NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE RESTRICT
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_goals_project ON goals(project_id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_goals_status ON goals(status)")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_goal_checkins_goal ON goal_checkins(goal_id)"
            )

    @staticmethod
    def _validate_status(status: str) -> str:
        normalized = status.strip().lower()
        if normalized not in ALLOWED_GOAL_STATUSES:
            raise ValueError("Status de objetivo inválido.")
        return normalized

    @staticmethod
    def _validate_direction(direction: str) -> str:
        normalized = direction.strip().lower()
        if normalized not in ALLOWED_GOAL_DIRECTIONS:
            raise ValueError("Direção de objetivo inválida.")
        return normalized

    def create_goal(
        self,
        title: str,
        *,
        metric: str,
        target: float,
        baseline: float = 0,
        current: float | None = None,
        project_id: int | None = None,
        description: str = "",
        direction: str = "increase",
        unit: str = "",
        status: str = "planned",
        due_at: str | None = None,
    ) -> Goal:
        clean_title = title.strip()
        clean_metric = metric.strip()
        if not clean_title:
            raise ValueError("O título do objetivo não pode ficar vazio.")
        if not clean_metric:
            raise ValueError("A métrica do objetivo não pode ficar vazia.")
        normalized_status = self._validate_status(status)
        normalized_direction = self._validate_direction(direction)
        initial = float(baseline if current is None else current)
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO goals(
                    project_id, title, description, metric, direction, baseline,
                    target, current, unit, status, due_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    clean_title,
                    description.strip(),
                    clean_metric,
                    normalized_direction,
                    float(baseline),
                    float(target),
                    initial,
                    unit.strip(),
                    normalized_status,
                    due_at,
                    now,
                    now,
                ),
            )
            goal_id = int(cursor.lastrowid)
        return self.get_goal(goal_id)

    def get_goal(self, goal_id: int) -> Goal:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if row is None:
            raise KeyError(f"Objetivo {goal_id} não encontrado.")
        return Goal(**dict(row))

    def list_goals(
        self,
        *,
        project_id: int | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Goal]:
        clauses: list[str] = []
        values: list[object] = []
        if project_id is not None:
            clauses.append("project_id = ?")
            values.append(project_id)
        if status is not None:
            clauses.append("status = ?")
            values.append(self._validate_status(status))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(max(1, limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM goals{where} ORDER BY updated_at DESC, id DESC LIMIT ?",
                values,
            ).fetchall()
        return [Goal(**dict(row)) for row in rows]

    def update_status(self, goal_id: int, status: str) -> Goal:
        normalized = self._validate_status(status)
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE goals SET status = ?, updated_at = ? WHERE id = ?",
                (normalized, self._now(), goal_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Objetivo {goal_id} não encontrado.")
        return self.get_goal(goal_id)

    def check_in(self, goal_id: int, value: float, *, note: str = "") -> GoalCheckIn:
        goal = self.get_goal(goal_id)
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO goal_checkins(goal_id, value, note, created_at) VALUES (?, ?, ?, ?)",
                (goal_id, float(value), note.strip(), now),
            )
            connection.execute(
                "UPDATE goals SET current = ?, updated_at = ? WHERE id = ?",
                (float(value), now, goal.id),
            )
            checkin_id = int(cursor.lastrowid)
        return self.get_checkin(checkin_id)

    def get_checkin(self, checkin_id: int) -> GoalCheckIn:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM goal_checkins WHERE id = ?", (checkin_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Medição {checkin_id} não encontrada.")
        return GoalCheckIn(**dict(row))

    def list_checkins(self, goal_id: int, *, limit: int = 100) -> list[GoalCheckIn]:
        self.get_goal(goal_id)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM goal_checkins WHERE goal_id = ? ORDER BY id DESC LIMIT ?",
                (goal_id, max(1, limit)),
            ).fetchall()
        return [GoalCheckIn(**dict(row)) for row in rows]


__all__ = [
    "ALLOWED_GOAL_DIRECTIONS",
    "ALLOWED_GOAL_STATUSES",
    "Goal",
    "GoalCheckIn",
    "GoalStore",
]
