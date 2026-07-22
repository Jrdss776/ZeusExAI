"""Executor local controlado para planos aprovados do Agent Runtime.

A Fase 17.3 executa somente ações locais, registradas e idempotentes. Integrações
externas, shell arbitrário e ações não aprovadas permanecem bloqueados.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
import hashlib
import json
import sqlite3

from openjarvis.zeusex.agent_plan_queue import AgentPlanQueue, PlanQueueStatus
from openjarvis.zeusex.local_automation import list_local_files, system_information


LocalActionHandler = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class LocalActionDefinition:
    name: str
    handler: LocalActionHandler
    description: str
    permission: str
    local_only: bool = True
    idempotent: bool = True


@dataclass(frozen=True, slots=True)
class LocalExecutionReceipt:
    id: int
    queue_id: int
    plan_id: str
    action: str
    idempotency_key: str
    status: str
    output: str
    executed_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_EXTERNAL_PREFIXES = (
    "calendar.", "gmail.", "drive.", "github.", "whatsapp.",
    "telegram.", "slack.", "http.", "shell.", "subprocess.",
)


class LocalAgentExecutor:
    """Executa ações locais aprovadas com registro de idempotência em SQLite."""

    def __init__(
        self,
        queue: AgentPlanQueue,
        database_path: Path | str,
        actions: Mapping[str, LocalActionDefinition] | None = None,
    ) -> None:
        self.queue = queue
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._actions: dict[str, LocalActionDefinition] = {}
        self._initialize()
        for definition in (actions or self.default_actions()).values():
            self.register(definition)

    @staticmethod
    def default_actions() -> dict[str, LocalActionDefinition]:
        return {
            "system.information": LocalActionDefinition(
                "system.information",
                system_information,
                "Ler informações básicas e não pessoais do ambiente local.",
                "system.read_basic",
            ),
            "filesystem.list_directory": LocalActionDefinition(
                "filesystem.list_directory",
                list_local_files,
                "Listar até 50 entradas de um diretório local, sem recursão.",
                "filesystem.read_directory",
            ),
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS local_agent_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id INTEGER NOT NULL,
                    plan_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    output TEXT NOT NULL,
                    executed_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_local_agent_executions_queue "
                "ON local_agent_executions(queue_id)"
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row(row: sqlite3.Row) -> LocalExecutionReceipt:
        return LocalExecutionReceipt(
            id=int(row["id"]),
            queue_id=int(row["queue_id"]),
            plan_id=str(row["plan_id"]),
            action=str(row["action"]),
            idempotency_key=str(row["idempotency_key"]),
            status=str(row["status"]),
            output=str(row["output"]),
            executed_at=str(row["executed_at"]),
        )

    def register(self, definition: LocalActionDefinition) -> None:
        name = definition.name.strip().lower()
        if not name or name != definition.name:
            raise ValueError("O nome da ação precisa estar normalizado em minúsculas.")
        if name.startswith(_EXTERNAL_PREFIXES):
            raise PermissionError("Integrações externas não podem ser registradas no executor local.")
        if not definition.local_only or not definition.idempotent:
            raise PermissionError("A ação precisa ser local_only e idempotent.")
        if not callable(definition.handler):
            raise TypeError("handler precisa ser chamável.")
        self._actions[name] = definition

    def status(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "mode": "local_confirmed",
            "registered_actions": sorted(self._actions),
            "external_actions_enabled": False,
            "shell_enabled": False,
        }

    def actions(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {
                "name": item.name,
                "description": item.description,
                "permission": item.permission,
                "local_only": item.local_only,
                "idempotent": item.idempotent,
            }
            for item in sorted(self._actions.values(), key=lambda value: value.name)
        )

    @staticmethod
    def _key(queue_id: int, plan_id: str, action: str, argument: str) -> str:
        payload = json.dumps(
            {"queue_id": queue_id, "plan_id": plan_id, "action": action, "argument": argument},
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_by_key(self, idempotency_key: str) -> LocalExecutionReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM local_agent_executions WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        return self._row(row) if row is not None else None

    def list_receipts(self, *, queue_id: int | None = None, limit: int = 50) -> list[LocalExecutionReceipt]:
        bounded = max(1, min(limit, 200))
        with self._connect() as connection:
            if queue_id is None:
                rows = connection.execute(
                    "SELECT * FROM local_agent_executions ORDER BY id DESC LIMIT ?", (bounded,)
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM local_agent_executions WHERE queue_id = ? ORDER BY id DESC LIMIT ?",
                    (queue_id, bounded),
                ).fetchall()
        return [self._row(row) for row in rows]

    def execute(
        self,
        queue_id: int,
        action: str,
        *,
        argument: str = "",
        confirmed: bool = False,
    ) -> LocalExecutionReceipt:
        queued = self.queue.get(queue_id)
        if queued.status != PlanQueueStatus.APPROVED.value:
            raise PermissionError("A execução exige um plano aprovado e não expirado.")
        if not confirmed:
            raise PermissionError("A execução local exige confirmação explícita.")

        normalized = action.strip().lower()
        if normalized.startswith(_EXTERNAL_PREFIXES):
            raise PermissionError("Ações externas não são permitidas na Fase 17.3.")
        definition = self._actions.get(normalized)
        if definition is None:
            raise PermissionError("Ação local não registrada.")
        if not definition.local_only or not definition.idempotent:
            raise PermissionError("Ação incompatível com a política local do executor.")

        clean_argument = argument.strip()
        key = self._key(queue_id, queued.plan_id, normalized, clean_argument)
        existing = self.get_by_key(key)
        if existing is not None:
            return existing

        output = str(definition.handler(clean_argument))
        executed_at = self._now()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO local_agent_executions(
                    queue_id, plan_id, action, idempotency_key, status, output, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (queue_id, queued.plan_id, normalized, key, "succeeded", output, executed_at),
            )
            receipt_id = int(cursor.lastrowid)
        return LocalExecutionReceipt(
            receipt_id, queue_id, queued.plan_id, normalized, key, "succeeded", output, executed_at
        )


__all__ = [
    "LocalActionDefinition",
    "LocalAgentExecutor",
    "LocalExecutionReceipt",
]
