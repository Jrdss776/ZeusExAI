"""Auditoria JSONL leve para ações sensíveis da agente Vampira."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ProductivityAuditEvent:
    action: str
    decision: str
    reason: str
    resource_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProductivityAuditSink(Protocol):
    def record(
        self,
        action: str,
        decision: str,
        reason: str,
        *,
        resource_id: str = "",
    ) -> ProductivityAuditEvent | None:
        """Registra metadados mínimos, nunca conteúdo de e-mail ou tarefa."""


class NullProductivityAudit:
    def record(self, *_: Any, **__: Any) -> None:
        return None


class JsonlProductivityAudit:
    """Grava um evento por linha, sem manter eventos residentes em memória."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    @staticmethod
    def _clean(value: str, limit: int = 200) -> str:
        return " ".join(str(value).split())[:limit]

    def record(
        self,
        action: str,
        decision: str,
        reason: str,
        *,
        resource_id: str = "",
    ) -> ProductivityAuditEvent:
        event = ProductivityAuditEvent(
            action=self._clean(action, 80),
            decision=self._clean(decision, 40),
            reason=self._clean(reason),
            resource_id=self._clean(resource_id, 120),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        line = json.dumps(event.to_dict(), ensure_ascii=False, separators=(",", ":"))
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return event


def build_productivity_audit_from_env() -> ProductivityAuditSink:
    """Ativa auditoria somente quando um caminho local foi configurado."""

    path = os.getenv("ZEUSEX_VAMPIRA_AUDIT_LOG", "").strip()
    return JsonlProductivityAudit(Path(path).expanduser()) if path else NullProductivityAudit()


__all__ = [
    "JsonlProductivityAudit",
    "NullProductivityAudit",
    "ProductivityAuditEvent",
    "ProductivityAuditSink",
    "build_productivity_audit_from_env",
]
