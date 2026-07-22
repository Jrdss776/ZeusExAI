"""Gerenciador persistente de projetos do ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sqlite3


ALLOWED_PROJECT_STATUSES = frozenset({"planned", "active", "paused", "completed", "archived"})
ALLOWED_TASK_STATUSES = frozenset({"backlog", "todo", "in_progress", "blocked", "done"})
ALLOWED_PRIORITIES = frozenset({"low", "medium", "high", "critical"})


@dataclass(frozen=True, slots=True)
class Project:
    id: int
    name: str
    description: str
    status: str
    objective: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProjectTask:
    id: int
    project_id: int
    title: str
    description: str
    status: str
    priority: str
    due_at: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProjectStore:
    """Mantém projetos e tarefas em SQLite, sem executar ações externas."""

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
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    objective TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS project_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    due_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE RESTRICT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_tasks_project ON project_tasks(project_id)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_project_tasks_status ON project_tasks(status)"
            )

    @staticmethod
    def _validate_status(status: str) -> str:
        normalized = status.strip().lower()
        if normalized not in ALLOWED_PROJECT_STATUSES:
            raise ValueError("Status de projeto inválido.")
        return normalized

    @staticmethod
    def _validate_task_status(status: str) -> str:
        normalized = status.strip().lower()
        if normalized not in ALLOWED_TASK_STATUSES:
            raise ValueError("Status de tarefa inválido.")
        return normalized

    @staticmethod
    def _validate_priority(priority: str) -> str:
        normalized = priority.strip().lower()
        if normalized not in ALLOWED_PRIORITIES:
            raise ValueError("Prioridade inválida.")
        return normalized

    def create_project(
        self,
        name: str,
        *,
        description: str = "",
        objective: str | None = None,
        status: str = "planned",
    ) -> Project:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("O nome do projeto não pode ficar vazio.")
        normalized_status = self._validate_status(status)
        clean_objective = objective.strip() if objective and objective.strip() else None
        now = self._now()
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO projects(name, description, status, objective, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (clean_name, description.strip(), normalized_status, clean_objective, now, now),
                )
                project_id = int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Já existe um projeto chamado {clean_name}.") from exc
        return self.get_project(project_id)

    def get_project(self, project_id: int) -> Project:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(f"Projeto {project_id} não encontrado.")
        return Project(**dict(row))

    def list_projects(self, *, status: str | None = None, limit: int = 50) -> list[Project]:
        values: list[object] = []
        where = ""
        if status is not None:
            where = " WHERE status = ?"
            values.append(self._validate_status(status))
        values.append(max(1, limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM projects{where} ORDER BY updated_at DESC, id DESC LIMIT ?",
                values,
            ).fetchall()
        return [Project(**dict(row)) for row in rows]

    def update_project_status(self, project_id: int, status: str) -> Project:
        normalized_status = self._validate_status(status)
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
                (normalized_status, self._now(), project_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Projeto {project_id} não encontrado.")
        return self.get_project(project_id)

    def add_task(
        self,
        project_id: int,
        title: str,
        *,
        description: str = "",
        status: str = "todo",
        priority: str = "medium",
        due_at: str | None = None,
    ) -> ProjectTask:
        self.get_project(project_id)
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("O título da tarefa não pode ficar vazio.")
        normalized_status = self._validate_task_status(status)
        normalized_priority = self._validate_priority(priority)
        now = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO project_tasks(
                    project_id, title, description, status, priority, due_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    clean_title,
                    description.strip(),
                    normalized_status,
                    normalized_priority,
                    due_at,
                    now,
                    now,
                ),
            )
            task_id = int(cursor.lastrowid)
        return self.get_task(task_id)

    def get_task(self, task_id: int) -> ProjectTask:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM project_tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"Tarefa {task_id} não encontrada.")
        return ProjectTask(**dict(row))

    def list_tasks(
        self,
        project_id: int,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[ProjectTask]:
        self.get_project(project_id)
        clauses = ["project_id = ?"]
        values: list[object] = [project_id]
        if status is not None:
            clauses.append("status = ?")
            values.append(self._validate_task_status(status))
        values.append(max(1, limit))
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM project_tasks WHERE {' AND '.join(clauses)} "
                "ORDER BY CASE priority WHEN 'critical' THEN 4 WHEN 'high' THEN 3 "
                "WHEN 'medium' THEN 2 ELSE 1 END DESC, id DESC LIMIT ?",
                values,
            ).fetchall()
        return [ProjectTask(**dict(row)) for row in rows]

    def update_task_status(self, task_id: int, status: str) -> ProjectTask:
        normalized_status = self._validate_task_status(status)
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE project_tasks SET status = ?, updated_at = ? WHERE id = ?",
                (normalized_status, self._now(), task_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Tarefa {task_id} não encontrada.")
        return self.get_task(task_id)


__all__ = [
    "ALLOWED_PRIORITIES",
    "ALLOWED_PROJECT_STATUSES",
    "ALLOWED_TASK_STATUSES",
    "Project",
    "ProjectStore",
    "ProjectTask",
]
