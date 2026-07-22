"""Runtime seguro de planejamento do agente ZeusExAI.

A Fase 17.1 é deliberadamente *plan-only*: o runtime consulta contexto local,
classifica a intenção e produz um plano explicável. Ele não despacha handlers,
não chama conectores externos e não executa mutações.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence
import uuid

from openjarvis.zeusex.orchestrator import CommandDecision, CommandDomain, CommandOrchestrator


class AgentRuntimeMode(str, Enum):
    DISABLED = "disabled"
    PLAN_ONLY = "plan_only"


class PlanStepKind(str, Enum):
    ANALYZE = "analyze"
    READ_CONTEXT = "read_context"
    PREPARE = "prepare"
    REVIEW = "review"
    REQUEST_CONFIRMATION = "request_confirmation"


@dataclass(frozen=True, slots=True)
class AgentRuntimeStatus:
    enabled: bool
    mode: str
    can_plan: bool
    can_execute: bool = False
    external_actions_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AgentPlanStep:
    id: str
    order: int
    kind: str
    title: str
    description: str
    domain: str
    requires_confirmation: bool = False
    executable: bool = False
    blocked_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AgentContextSnapshot:
    dashboard_summary: dict[str, int | float]
    dashboard_alerts: tuple[dict[str, Any], ...]
    integration_summary: dict[str, Any]
    integration_alerts: tuple[dict[str, Any], ...]
    memories: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dashboard_summary": self.dashboard_summary,
            "dashboard_alerts": list(self.dashboard_alerts),
            "integration_summary": self.integration_summary,
            "integration_alerts": list(self.integration_alerts),
            "memories": list(self.memories),
        }


@dataclass(frozen=True, slots=True)
class AgentPlan:
    id: str
    command: str
    created_at: str
    mode: str
    decision: CommandDecision
    context: AgentContextSnapshot
    steps: tuple[AgentPlanStep, ...]
    requires_confirmation: bool
    executable: bool = False
    execution_blocked_reason: str = "A Fase 17.1 produz planos, mas não executa ações."

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "command": self.command,
            "created_at": self.created_at,
            "mode": self.mode,
            "decision": self.decision.to_dict(),
            "context": self.context.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "requires_confirmation": self.requires_confirmation,
            "executable": self.executable,
            "execution_blocked_reason": self.execution_blocked_reason,
        }


class DashboardReader(Protocol):
    def build(self, *, limit: int = 10) -> Any: ...


class IntegrationReader(Protocol):
    def overview(self) -> Any: ...


class MemoryReader(Protocol):
    def search(self, query: str, *, limit: int = 20) -> Sequence[Any]: ...


_DOMAIN_PREPARATION: dict[CommandDomain, tuple[str, str]] = {
    CommandDomain.PROJECT: (
        "Preparar atualização do projeto",
        "Organizar projetos, tarefas prioritárias, bloqueios e próximos marcos sem alterar registros.",
    ),
    CommandDomain.MEMORY: (
        "Revisar memória relevante",
        "Selecionar memórias relacionadas e apontar lacunas sem gravar novas informações.",
    ),
    CommandDomain.COMMERCIAL_ANALYSIS: (
        "Preparar análise comercial",
        "Organizar dados disponíveis, premissas ausentes e cálculos necessários antes da análise.",
    ),
    CommandDomain.CAMPAIGN: (
        "Preparar campanha",
        "Estruturar objetivo, público, canal e conteúdo para revisão humana antes de publicar.",
    ),
    CommandDomain.ACHADINHOS: (
        "Preparar seleção de produtos",
        "Reunir critérios e produtos disponíveis sem publicar ou enviar ofertas.",
    ),
    CommandDomain.AGENDA: (
        "Preparar ação de agenda",
        "Revisar compromissos e montar uma proposta sem criar ou modificar eventos.",
    ),
    CommandDomain.DASHBOARD: (
        "Interpretar o painel",
        "Resumir alertas, prioridades e progresso com base no snapshot local.",
    ),
    CommandDomain.DEVELOPMENT: (
        "Preparar trabalho de desenvolvimento",
        "Organizar repositório, CI, riscos e mudanças propostas sem escrever no GitHub.",
    ),
    CommandDomain.ASSISTANT: (
        "Preparar resposta assistiva",
        "Organizar a solicitação e apresentar uma resposta ou pedir apenas os dados indispensáveis.",
    ),
}


class AgentRuntime:
    """Produz planos locais e explicáveis sem executar qualquer etapa."""

    def __init__(
        self,
        orchestrator: CommandOrchestrator,
        dashboard: DashboardReader,
        integrations: IntegrationReader,
        memories: MemoryReader,
        *,
        mode: AgentRuntimeMode = AgentRuntimeMode.PLAN_ONLY,
        context_limit: int = 10,
    ) -> None:
        if not 1 <= context_limit <= 50:
            raise ValueError("context_limit precisa estar entre 1 e 50.")
        self.orchestrator = orchestrator
        self.dashboard = dashboard
        self.integrations = integrations
        self.memories = memories
        self.mode = AgentRuntimeMode(mode)
        self.context_limit = context_limit

    def status(self) -> AgentRuntimeStatus:
        enabled = self.mode is AgentRuntimeMode.PLAN_ONLY
        return AgentRuntimeStatus(
            enabled=enabled,
            mode=self.mode.value,
            can_plan=enabled,
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _safe_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            result = to_dict()
            if isinstance(result, Mapping):
                return dict(result)
        return {}

    def _snapshot(self, command: str) -> AgentContextSnapshot:
        dashboard_data = self._safe_dict(self.dashboard.build(limit=self.context_limit))
        integration_data = self._safe_dict(self.integrations.overview())
        memories = self.memories.search(command, limit=self.context_limit)

        memory_items = tuple(self._safe_dict(item) for item in memories)
        dashboard_alerts = dashboard_data.get("alerts", [])
        integration_alerts = integration_data.get("alerts", [])

        return AgentContextSnapshot(
            dashboard_summary=dict(dashboard_data.get("summary", {})),
            dashboard_alerts=tuple(
                dict(item) for item in dashboard_alerts if isinstance(item, Mapping)
            ),
            integration_summary=dict(integration_data.get("summary", {})),
            integration_alerts=tuple(
                dict(item) for item in integration_alerts if isinstance(item, Mapping)
            ),
            memories=memory_items,
        )

    @staticmethod
    def _step(
        order: int,
        kind: PlanStepKind,
        title: str,
        description: str,
        domain: CommandDomain,
        *,
        requires_confirmation: bool = False,
    ) -> AgentPlanStep:
        return AgentPlanStep(
            id=f"step-{order}",
            order=order,
            kind=kind.value,
            title=title,
            description=description,
            domain=domain.value,
            requires_confirmation=requires_confirmation,
            executable=False,
            blocked_reason="Execução não está disponível no modo plan_only.",
        )

    def plan(
        self,
        command: str,
        context: Mapping[str, Any] | None = None,
    ) -> AgentPlan:
        del context  # reservado para a Fase 17.2; não é persistido nesta fase
        clean_command = command.strip()
        if not clean_command:
            raise ValueError("command não pode ficar vazio.")
        if len(clean_command) > 10_000:
            raise ValueError("command não pode exceder 10000 caracteres.")
        if self.mode is AgentRuntimeMode.DISABLED:
            raise PermissionError("Agent Runtime está desativado.")

        decision = self.orchestrator.route(clean_command)
        snapshot = self._snapshot(clean_command)
        preparation_title, preparation_description = _DOMAIN_PREPARATION[decision.domain]

        steps: list[AgentPlanStep] = [
            self._step(
                1,
                PlanStepKind.ANALYZE,
                "Classificar a solicitação",
                "Confirmar domínio, intenção e sinais de ação sensível usando classificação local.",
                decision.domain,
            ),
            self._step(
                2,
                PlanStepKind.READ_CONTEXT,
                "Consultar contexto disponível",
                "Ler dashboard, memória e estado sanitizado das integrações sem executar mutações.",
                decision.domain,
            ),
            self._step(
                3,
                PlanStepKind.PREPARE,
                preparation_title,
                preparation_description,
                decision.domain,
                requires_confirmation=decision.requires_confirmation,
            ),
            self._step(
                4,
                PlanStepKind.REVIEW,
                "Apresentar proposta para revisão",
                "Expor premissas, dados ausentes, riscos e resultado esperado antes de qualquer ação futura.",
                decision.domain,
            ),
        ]
        if decision.requires_confirmation:
            steps.append(
                self._step(
                    5,
                    PlanStepKind.REQUEST_CONFIRMATION,
                    "Solicitar confirmação explícita",
                    "A ação solicitada contém termo sensível e não pode avançar sem confirmação específica.",
                    decision.domain,
                    requires_confirmation=True,
                )
            )

        return AgentPlan(
            id=f"plan-{uuid.uuid4().hex}",
            command=clean_command,
            created_at=self._now(),
            mode=self.mode.value,
            decision=decision,
            context=snapshot,
            steps=tuple(steps),
            requires_confirmation=decision.requires_confirmation,
        )

    def execute(self, plan: AgentPlan, *, confirmed: bool = False) -> None:
        del plan, confirmed
        raise PermissionError("A Fase 17.1 não executa planos.")


__all__ = [
    "AgentContextSnapshot",
    "AgentPlan",
    "AgentPlanStep",
    "AgentRuntime",
    "AgentRuntimeMode",
    "AgentRuntimeStatus",
    "PlanStepKind",
]
