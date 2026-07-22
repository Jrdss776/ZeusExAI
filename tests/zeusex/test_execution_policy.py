from pathlib import Path

import pytest

from openjarvis.zeusex.execution_audit import ExecutionAuditStore
from openjarvis.zeusex.execution_policy import ActionExecutionPolicy
from openjarvis.zeusex.policy_controlled_executor import PolicyControlledExecutor


class FakeReceipt:
    def to_dict(self):
        return {"status": "succeeded"}


class FakeExecutor:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, queue_id, action, *, argument="", confirmed=False):
        if not confirmed:
            raise PermissionError("confirmation required")
        self.calls += 1
        return FakeReceipt()


def build(tmp_path: Path, *, attempts=3, hourly=20, max_argument=20):
    executor = FakeExecutor()
    audit = ExecutionAuditStore(tmp_path / "audit.db")
    policy = ActionExecutionPolicy("system.information", attempts, hourly, 5.0, max_argument)
    controlled = PolicyControlledExecutor(executor, audit, {policy.action: policy})
    return executor, audit, controlled


def test_policy_validation():
    with pytest.raises(ValueError):
        ActionExecutionPolicy("INVALID")
    with pytest.raises(ValueError):
        ActionExecutionPolicy("x", max_attempts_per_plan=0)


def test_success_is_audited(tmp_path):
    executor, audit, controlled = build(tmp_path)
    controlled.execute(1, "system.information", confirmed=True)
    events = audit.list(queue_id=1)
    assert executor.calls == 1
    assert {item.event for item in events} == {"attempt", "completed"}


def test_unknown_action_is_blocked_and_audited(tmp_path):
    _, audit, controlled = build(tmp_path)
    with pytest.raises(PermissionError):
        controlled.execute(1, "github.issue", confirmed=True)
    assert any(item.event == "blocked" for item in audit.list(queue_id=1))


def test_argument_limit(tmp_path):
    _, audit, controlled = build(tmp_path, max_argument=2)
    with pytest.raises(ValueError):
        controlled.execute(1, "system.information", argument="abc", confirmed=True)
    assert audit.list(queue_id=1)[0].reason == "Argumento excede o limite."


def test_attempt_limit(tmp_path):
    _, _, controlled = build(tmp_path, attempts=1)
    controlled.execute(1, "system.information", confirmed=True)
    with pytest.raises(PermissionError):
        controlled.execute(1, "system.information", argument="different", confirmed=True)


def test_hourly_limit(tmp_path):
    _, _, controlled = build(tmp_path, hourly=1)
    controlled.execute(1, "system.information", confirmed=True)
    with pytest.raises(PermissionError):
        controlled.execute(2, "system.information", confirmed=True)


def test_failed_confirmation_is_audited(tmp_path):
    _, audit, controlled = build(tmp_path)
    with pytest.raises(PermissionError):
        controlled.execute(1, "system.information", confirmed=False)
    assert audit.list(queue_id=1)[0].event == "failed"


def test_status_remains_local_only(tmp_path):
    _, _, controlled = build(tmp_path)
    status = controlled.status()
    assert status["external_actions_enabled"] is False
    assert status["shell_enabled"] is False
    assert status["hard_process_termination"] is False
