from __future__ import annotations

from dataclasses import dataclass

import pytest

from openjarvis.zeusex.local_agent_executor import (
    LocalActionDefinition,
    LocalAgentExecutor,
)
from openjarvis.zeusex.local_agent_executor_api import LocalAgentExecutorAPI


@dataclass
class FakeQueuedPlan:
    id: int = 1
    plan_id: str = "plan-test"
    status: str = "approved"


class FakeQueue:
    def __init__(self, status: str = "approved") -> None:
        self.item = FakeQueuedPlan(status=status)

    def get(self, queue_id: int) -> FakeQueuedPlan:
        assert queue_id == 1
        return self.item


def build_executor(tmp_path, *, status: str = "approved") -> LocalAgentExecutor:
    return LocalAgentExecutor(FakeQueue(status), tmp_path / "executor.sqlite3")


def test_status_exposes_only_local_safe_capabilities(tmp_path) -> None:
    executor = build_executor(tmp_path)

    status = executor.status()

    assert status["mode"] == "local_confirmed"
    assert status["external_actions_enabled"] is False
    assert status["shell_enabled"] is False
    assert status["registered_actions"] == [
        "filesystem.list_directory",
        "system.information",
    ]


def test_execute_requires_approved_plan(tmp_path) -> None:
    executor = build_executor(tmp_path, status="pending")

    with pytest.raises(PermissionError, match="plano aprovado"):
        executor.execute(1, "system.information", confirmed=True)


def test_execute_requires_explicit_confirmation(tmp_path) -> None:
    executor = build_executor(tmp_path)

    with pytest.raises(PermissionError, match="confirmação explícita"):
        executor.execute(1, "system.information")


def test_unregistered_and_external_actions_are_blocked(tmp_path) -> None:
    executor = build_executor(tmp_path)

    with pytest.raises(PermissionError, match="não registrada"):
        executor.execute(1, "local.unknown", confirmed=True)

    with pytest.raises(PermissionError, match="externas"):
        executor.execute(1, "github.create_issue", confirmed=True)


def test_registration_rejects_external_or_non_idempotent_actions(tmp_path) -> None:
    executor = build_executor(tmp_path)

    with pytest.raises(PermissionError, match="externas"):
        executor.register(
            LocalActionDefinition(
                "gmail.send",
                lambda value: value,
                "external",
                "gmail.send",
            )
        )

    with pytest.raises(PermissionError, match="idempotent"):
        executor.register(
            LocalActionDefinition(
                "local.counter",
                lambda value: value,
                "unsafe",
                "system.sensitive_action",
                idempotent=False,
            )
        )


def test_execution_is_idempotent_and_persists_receipt(tmp_path) -> None:
    executor = build_executor(tmp_path)

    first = executor.execute(1, "system.information", confirmed=True)
    second = executor.execute(1, "system.information", confirmed=True)

    assert first.id == second.id
    assert first.idempotency_key == second.idempotency_key
    assert first.status == "succeeded"
    assert "Python:" in first.output
    assert len(executor.list_receipts(queue_id=1)) == 1


def test_different_argument_creates_a_distinct_receipt(tmp_path) -> None:
    executor = build_executor(tmp_path)

    first = executor.execute(1, "filesystem.list_directory", argument=str(tmp_path), confirmed=True)
    second = executor.execute(1, "filesystem.list_directory", argument=".", confirmed=True)

    assert first.id != second.id
    assert len(executor.list_receipts()) == 2


def test_api_delegates_execution_and_lists_receipts(tmp_path) -> None:
    api = LocalAgentExecutorAPI(build_executor(tmp_path))

    result = api.execute(
        1,
        {"action": "system.information", "argument": "", "confirmed": True},
    )
    receipts = api.receipts(queue_id=1)
    actions = api.actions()

    assert result["status"] == "succeeded"
    assert receipts["count"] == 1
    assert actions["count"] == 2
