"""Composicao persistente e somente leitura da governanca do Agent Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openjarvis.zeusex.agent_governance_dashboard import AgentGovernanceDashboard
from openjarvis.zeusex.agent_governance_dashboard_api import AgentGovernanceDashboardAPI
from openjarvis.zeusex.agent_governance_history import AgentGovernanceHistory
from openjarvis.zeusex.agent_governance_history_api import AgentGovernanceHistoryAPI
from openjarvis.zeusex.agent_plan_queue import AgentPlanQueue
from openjarvis.zeusex.execution_audit import ExecutionAuditStore
from openjarvis.zeusex.execution_policy import default_execution_policies
from openjarvis.zeusex.local_agent_executor import LocalAgentExecutor


@dataclass(frozen=True, slots=True)
class GovernanceRuntimeAPIs:
    """APIs de consulta que compartilham os mesmos bancos persistentes."""

    dashboard: AgentGovernanceDashboardAPI
    history: AgentGovernanceHistoryAPI


def build_governance_runtime_apis(data_dir: Path | str) -> GovernanceRuntimeAPIs:
    """Monta as consultas de governanca sem expor aprovacao ou execucao."""

    root = Path(data_dir)
    queue = AgentPlanQueue(root / "agent-plan-queue.db")
    executor = LocalAgentExecutor(queue, root / "agent-executions.db")
    audit = ExecutionAuditStore(root / "agent-execution-audit.db")
    policies = default_execution_policies()
    return GovernanceRuntimeAPIs(
        dashboard=AgentGovernanceDashboardAPI(
            AgentGovernanceDashboard(queue, executor, audit, policies)
        ),
        history=AgentGovernanceHistoryAPI(
            AgentGovernanceHistory(queue, executor, audit)
        ),
    )


__all__ = ["GovernanceRuntimeAPIs", "build_governance_runtime_apis"]
