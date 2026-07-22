"""Relatórios históricos locais e somente leitura para governança do agente."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class GovernanceHistoryReport:
    generated_at: str
    period: dict[str, str | int]
    totals: dict[str, int]
    plans_by_status: dict[str, int]
    executions_by_status: dict[str, int]
    audit_by_event: dict[str, int]
    audit_by_action: dict[str, int]
    daily: tuple[dict[str, Any], ...]
    read_only: bool = True
    external_actions_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["daily"] = list(self.daily)
        return data


class AgentGovernanceHistory:
    """Consolida dados existentes sem alterar fila, recibos ou auditoria."""

    def __init__(self, queue: Any, executor: Any, audit: Any) -> None:
        self.queue = queue
        self.executor = executor
        self.audit = audit

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse(value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _increment(target: dict[str, int], key: str) -> None:
        normalized = key.strip().lower() or "unknown"
        target[normalized] = target.get(normalized, 0) + 1

    def build(self, *, days: int = 30, limit: int = 500) -> GovernanceHistoryReport:
        if not 1 <= days <= 365:
            raise ValueError("days precisa estar entre 1 e 365.")
        bounded = max(1, min(limit, 500))
        now = self._now()
        since = now - timedelta(days=days)

        plans = self.queue.list(limit=bounded)
        receipts = self.executor.list_receipts(limit=min(bounded, 200))
        events = self.audit.list(limit=bounded)

        plans_by_status: dict[str, int] = {}
        executions_by_status: dict[str, int] = {}
        audit_by_event: dict[str, int] = {}
        audit_by_action: dict[str, int] = {}
        daily_map: dict[str, dict[str, int | str]] = {}

        def bucket(moment: datetime) -> dict[str, int | str]:
            key = moment.date().isoformat()
            return daily_map.setdefault(
                key,
                {"date": key, "plans": 0, "executions": 0, "audit_events": 0, "blocked": 0, "failed": 0, "timeouts": 0},
            )

        visible_plans = 0
        for item in plans:
            moment = self._parse(getattr(item, "created_at", None))
            if moment is None or moment < since or moment > now:
                continue
            visible_plans += 1
            self._increment(plans_by_status, str(getattr(item, "status", "unknown")))
            bucket(moment)["plans"] += 1  # type: ignore[operator]

        visible_receipts = 0
        for item in receipts:
            moment = self._parse(getattr(item, "executed_at", None))
            if moment is None or moment < since or moment > now:
                continue
            visible_receipts += 1
            self._increment(executions_by_status, str(getattr(item, "status", "unknown")))
            bucket(moment)["executions"] += 1  # type: ignore[operator]

        visible_events = 0
        for item in events:
            moment = self._parse(getattr(item, "created_at", None))
            if moment is None or moment < since or moment > now:
                continue
            visible_events += 1
            event = str(getattr(item, "event", "unknown")).strip().lower()
            action = str(getattr(item, "action", "unknown"))
            self._increment(audit_by_event, event)
            self._increment(audit_by_action, action)
            day = bucket(moment)
            day["audit_events"] += 1  # type: ignore[operator]
            if event == "blocked":
                day["blocked"] += 1  # type: ignore[operator]
            elif event == "failed":
                day["failed"] += 1  # type: ignore[operator]
            elif event == "timeout":
                day["timeouts"] += 1  # type: ignore[operator]

        totals = {
            "plans": visible_plans,
            "executions": visible_receipts,
            "audit_events": visible_events,
            "blocked": audit_by_event.get("blocked", 0),
            "failed": audit_by_event.get("failed", 0),
            "timeouts": audit_by_event.get("timeout", 0),
        }
        return GovernanceHistoryReport(
            generated_at=now.isoformat(),
            period={"days": days, "from": since.isoformat(), "to": now.isoformat()},
            totals=totals,
            plans_by_status=dict(sorted(plans_by_status.items())),
            executions_by_status=dict(sorted(executions_by_status.items())),
            audit_by_event=dict(sorted(audit_by_event.items())),
            audit_by_action=dict(sorted(audit_by_action.items())),
            daily=tuple(daily_map[key] for key in sorted(daily_map)),
        )


__all__ = ["AgentGovernanceHistory", "GovernanceHistoryReport"]
