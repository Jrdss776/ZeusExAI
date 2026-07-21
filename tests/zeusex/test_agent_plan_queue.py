from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from openjarvis.zeusex.agent_plan_queue import AgentPlanQueue, PlanQueueStatus


class Domain:
    value = "development"


class Decision:
    domain = Domain()


class FakePlan:
    id = "plan-1"
    command = "revisar github"
    decision = Decision()
    requires_confirmation = False

    def to_dict(self):
        return {
            "id": self.id,
            "command": self.command,
            "decision": {"domain": "development"},
            "requires_confirmation": False,
            "executable": False,
        }


def test_enqueue_and_get(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    item = queue.enqueue(FakePlan())
    assert item.status == "pending"
    assert item.plan_id == "plan-1"
    assert item.payload["executable"] is False
    assert queue.get(item.id).command == "revisar github"


def test_approve_pending_plan(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    item = queue.enqueue(FakePlan())
    approved = queue.approve(item.id, note="Revisado")
    assert approved.status == "approved"
    assert approved.review_note == "Revisado"
    assert approved.reviewed_at is not None


def test_reject_pending_plan(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    item = queue.enqueue(FakePlan())
    rejected = queue.reject(item.id, note="Dados insuficientes")
    assert rejected.status == "rejected"
    assert rejected.review_note == "Dados insuficientes"


def test_review_transition_is_single_use(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    item = queue.enqueue(FakePlan())
    queue.approve(item.id)
    with pytest.raises(ValueError, match="Somente planos pendentes"):
        queue.reject(item.id)


def test_list_filters_status(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    first = queue.enqueue(FakePlan())
    queue.approve(first.id)

    class SecondPlan(FakePlan):
        id = "plan-2"

    queue.enqueue(SecondPlan())
    pending = queue.list(status=PlanQueueStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].plan_id == "plan-2"


def test_expire_due_marks_pending_plan(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    item = queue.enqueue(FakePlan())
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with queue._connect() as connection:
        connection.execute(
            "UPDATE agent_plan_queue SET expires_at = ? WHERE id = ?",
            (past, item.id),
        )
    assert queue.expire_due() == 1
    assert queue.get(item.id).status == "expired"


def test_execute_is_always_blocked(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    item = queue.enqueue(FakePlan())
    queue.approve(item.id)
    with pytest.raises(PermissionError, match="não executa planos"):
        queue.execute(item.id, confirmed=True)


def test_invalid_ttl_is_rejected(tmp_path):
    queue = AgentPlanQueue(tmp_path / "queue.db")
    with pytest.raises(ValueError, match="ttl_minutes"):
        queue.enqueue(FakePlan(), ttl_minutes=0)
