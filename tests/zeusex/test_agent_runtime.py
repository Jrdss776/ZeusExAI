from dataclasses import dataclass

import pytest

from openjarvis.zeusex.agent_runtime import AgentRuntime, AgentRuntimeMode
from openjarvis.zeusex.agent_runtime_api import AgentRuntimeAPI
from openjarvis.zeusex.orchestrator import CommandOrchestrator


@dataclass
class FakeValue:
    value: dict

    def to_dict(self):
        return self.value


class FakeDashboard:
    def build(self, *, limit=10):
        assert limit == 10
        return FakeValue(
            {
                "summary": {"projects_active": 2, "open_tasks": 4},
                "alerts": [
                    {"level": "warning", "code": "priority_task", "message": "Revisar tarefa"}
                ],
            }
        )


class FakeIntegrations:
    def overview(self):
        return FakeValue(
            {
                "summary": {"total": 8, "ready": 2, "overall_state": "attention_required"},
                "alerts": [
                    {
                        "integration": "github",
                        "severity": "medium",
                        "code": "authentication_required",
                        "message": "Autenticação necessária.",
                    }
                ],
            }
        )


class FakeMemories:
    def search(self, query, *, limit=20):
        assert query
        assert limit == 10
        return [FakeValue({"id": 1, "category": "project", "content": "Decisão anterior"})]


def build_runtime(*, mode=AgentRuntimeMode.PLAN_ONLY):
    return AgentRuntime(
        CommandOrchestrator(),
        FakeDashboard(),
        FakeIntegrations(),
        FakeMemories(),
        mode=mode,
    )


def test_runtime_is_plan_only_and_cannot_execute() -> None:
    runtime = build_runtime()
    status = runtime.status()

    assert status.enabled is True
    assert status.can_plan is True
    assert status.can_execute is False
    assert status.external_actions_enabled is False


def test_plan_combines_decision_dashboard_integrations_and_memory() -> None:
    plan = build_runtime().plan("mostrar status do projeto")

    assert plan.decision.domain.value == "project"
    assert plan.executable is False
    assert plan.context.dashboard_summary["projects_active"] == 2
    assert plan.context.integration_summary["total"] == 8
    assert plan.context.memories[0]["content"] == "Decisão anterior"
    assert [step.order for step in plan.steps] == [1, 2, 3, 4]
    assert all(step.executable is False for step in plan.steps)


def test_sensitive_command_adds_confirmation_step_but_remains_unexecutable() -> None:
    plan = build_runtime().plan("enviar campanha")

    assert plan.requires_confirmation is True
    assert plan.executable is False
    assert plan.steps[-1].kind == "request_confirmation"
    assert plan.steps[-1].requires_confirmation is True


def test_disabled_runtime_blocks_planning() -> None:
    runtime = build_runtime(mode=AgentRuntimeMode.DISABLED)

    assert runtime.status().can_plan is False
    with pytest.raises(PermissionError, match="desativado"):
        runtime.plan("mostrar painel")


def test_runtime_never_executes_even_when_confirmed() -> None:
    runtime = build_runtime()
    plan = runtime.plan("mostrar painel")

    with pytest.raises(PermissionError, match="não executa"):
        runtime.execute(plan, confirmed=True)


def test_empty_and_oversized_commands_are_rejected() -> None:
    runtime = build_runtime()

    with pytest.raises(ValueError, match="vazio"):
        runtime.plan("  ")
    with pytest.raises(ValueError, match="10000"):
        runtime.plan("x" * 10_001)


def test_api_creates_plan_and_rejects_execution_route() -> None:
    api = AgentRuntimeAPI(build_runtime())

    status = api.dispatch("GET", "/v1/agent/status")
    created = api.dispatch("POST", "/v1/agent/plans", {"command": "abrir dashboard"})
    blocked = api.dispatch("POST", "/v1/agent/execute", {"plan_id": "anything"})

    assert status.status == 200
    assert status.body["status"]["can_execute"] is False
    assert created.status == 201
    assert created.body["plan"]["decision"]["domain"] == "dashboard"
    assert blocked.status == 405


def test_api_validates_context_object() -> None:
    response = AgentRuntimeAPI(build_runtime()).dispatch(
        "POST",
        "/v1/agent/plans",
        {"command": "mostrar painel", "context": ["invalid"]},
    )

    assert response.status == 400
