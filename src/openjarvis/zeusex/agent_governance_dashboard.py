"""Painel local somente leitura para governança do Agent Runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from openjarvis.zeusex.agent_plan_queue import AgentPlanQueue, PlanQueueStatus
from openjarvis.zeusex.execution_audit import ExecutionAuditStore
from openjarvis.zeusex.execution_policy import ActionExecutionPolicy
from openjarvis.zeusex.local_agent_executor import LocalAgentExecutor


@dataclass(frozen=True, slots=True)
class GovernanceAlert:
    level: str
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GovernanceSnapshot:
    generated_at: str
    summary: dict[str, int]
    queue: tuple[dict[str, Any], ...]
    receipts: tuple[dict[str, Any], ...]
    policies: tuple[dict[str, Any], ...]
    audit_events: tuple[dict[str, Any], ...]
    alerts: tuple[GovernanceAlert, ...]
    read_only: bool = True
    can_approve: bool = False
    can_execute: bool = False
    external_actions_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "summary": self.summary,
            "queue": list(self.queue),
            "receipts": list(self.receipts),
            "policies": list(self.policies),
            "audit_events": list(self.audit_events),
            "alerts": [item.to_dict() for item in self.alerts],
            "read_only": self.read_only,
            "can_approve": self.can_approve,
            "can_execute": self.can_execute,
            "external_actions_enabled": self.external_actions_enabled,
        }


class AgentGovernanceDashboard:
    """Agrega governança local sem alterar planos, políticas ou execuções."""

    def __init__(
        self,
        queue: AgentPlanQueue,
        executor: LocalAgentExecutor,
        audit: ExecutionAuditStore,
        policies: Mapping[str, ActionExecutionPolicy],
    ) -> None:
        self.queue = queue
        self.executor = executor
        self.audit = audit
        self.policies = dict(policies)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def build(self, *, limit: int = 50) -> GovernanceSnapshot:
        bounded = max(1, min(limit, 200))
        queue_items = self.queue.list(limit=bounded)
        receipts = self.executor.list_receipts(limit=bounded)
        audit_events = self.audit.list(limit=bounded)
        policies = tuple(
            item.to_dict() for item in sorted(self.policies.values(), key=lambda value: value.action)
        )

        by_status = {
            status.value: sum(item.status == status.value for item in queue_items)
            for status in PlanQueueStatus
        }
        by_event: dict[str, int] = {}
        for event in audit_events:
            by_event[event.event] = by_event.get(event.event, 0) + 1

        alerts: list[GovernanceAlert] = []
        if by_status[PlanQueueStatus.PENDING.value]:
            alerts.append(
                GovernanceAlert(
                    "warning",
                    "pending_reviews",
                    f"Há {by_status[PlanQueueStatus.PENDING.value]} plano(s) aguardando revisão.",
                )
            )
        blocked = by_event.get("blocked", 0)
        failed = by_event.get("failed", 0)
        timed_out = by_event.get("timeout", 0)
        if blocked:
            alerts.append(GovernanceAlert("warning", "blocked_executions", f"Há {blocked} bloqueio(s) recente(s)."))
        if failed:
            alerts.append(GovernanceAlert("high", "failed_executions", f"Há {failed} falha(s) recente(s)."))
        if timed_out:
            alerts.append(GovernanceAlert("high", "execution_timeouts", f"Há {timed_out} timeout(s) lógico(s)."))

        summary = {
            "plans_visible": len(queue_items),
            "plans_pending": by_status[PlanQueueStatus.PENDING.value],
            "plans_approved": by_status[PlanQueueStatus.APPROVED.value],
            "plans_rejected": by_status[PlanQueueStatus.REJECTED.value],
            "plans_expired": by_status[PlanQueueStatus.EXPIRED.value],
            "receipts_visible": len(receipts),
            "policies_total": len(policies),
            "audit_events_visible": len(audit_events),
            "audit_blocked": blocked,
            "audit_failed": failed,
            "audit_timeout": timed_out,
            "alerts_total": len(alerts),
        }

        return GovernanceSnapshot(
            generated_at=self._now(),
            summary=summary,
            queue=tuple(item.to_dict() for item in queue_items),
            receipts=tuple(item.to_dict() for item in receipts),
            policies=policies,
            audit_events=tuple(item.to_dict() for item in audit_events),
            alerts=tuple(alerts),
        )


__all__ = ["AgentGovernanceDashboard", "GovernanceAlert", "GovernanceSnapshot"]
