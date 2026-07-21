"""Dashboard inteligente unificado do ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.goals import GoalStore
from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.projects import ProjectStore
from openjarvis.zeusex.report_store import AnalysisReportStore


@dataclass(frozen=True, slots=True)
class DashboardAlert:
    level: str
    code: str
    message: str
    project_id: int | None = None
    goal_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    generated_at: str
    summary: dict[str, int | float]
    projects: tuple[dict[str, Any], ...]
    goals: tuple[dict[str, Any], ...]
    priority_tasks: tuple[dict[str, Any], ...]
    recent_memories: tuple[dict[str, Any], ...]
    top_products: tuple[dict[str, Any], ...]
    campaign_templates: tuple[dict[str, Any], ...]
    alerts: tuple[DashboardAlert, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "summary": self.summary,
            "projects": list(self.projects),
            "goals": list(self.goals),
            "priority_tasks": list(self.priority_tasks),
            "recent_memories": list(self.recent_memories),
            "top_products": list(self.top_products),
            "campaign_templates": list(self.campaign_templates),
            "alerts": [item.to_dict() for item in self.alerts],
        }


class IntelligentDashboardService:
    """Agrega dados locais sem executar ações externas ou destrutivas."""

    def __init__(
        self,
        projects: ProjectStore,
        goals: GoalStore,
        memories: IntelligentMemoryStore,
        reports: AnalysisReportStore,
        campaigns: CampaignTemplateStore,
    ) -> None:
        self.projects = projects
        self.goals = goals
        self.memories = memories
        self.reports = reports
        self.campaigns = campaigns

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def build(self, *, limit: int = 10) -> DashboardSnapshot:
        bounded = max(1, min(limit, 50))
        projects = self.projects.list_projects(limit=bounded)
        goals = self.goals.list_goals(limit=bounded)
        memories = self.memories.list(limit=bounded)
        reports = self.reports.top_products(limit=bounded, profitable_only=False)
        campaigns = self.campaigns.list(limit=bounded)

        priority_tasks = []
        open_tasks = 0
        blocked_tasks = 0
        for project in projects:
            for task in self.projects.list_tasks(project.id, limit=100):
                if task.status != "done":
                    open_tasks += 1
                if task.status == "blocked":
                    blocked_tasks += 1
                if task.priority in {"high", "critical"} and task.status != "done":
                    priority_tasks.append({"project_name": project.name, **task.to_dict()})
        priority_tasks.sort(
            key=lambda item: (item["priority"] != "critical", item["id"]),
        )

        active_goals = [goal for goal in goals if goal.status in {"planned", "active", "paused"}]
        average_progress = (
            round(sum(goal.progress_percent for goal in active_goals) / len(active_goals), 2)
            if active_goals
            else 0.0
        )

        alerts: list[DashboardAlert] = []
        for task in priority_tasks:
            level = "critical" if task["priority"] == "critical" else "warning"
            alerts.append(
                DashboardAlert(
                    level=level,
                    code="priority_task",
                    message=f"Tarefa {task['title']} requer atenção no projeto {task['project_name']}.",
                    project_id=int(task["project_id"]),
                )
            )
        for goal in active_goals:
            if goal.progress_percent < 25:
                alerts.append(
                    DashboardAlert(
                        level="warning",
                        code="goal_low_progress",
                        message=f"A meta {goal.title} está com {goal.progress_percent}% de progresso.",
                        project_id=goal.project_id,
                        goal_id=goal.id,
                    )
                )

        summary: dict[str, int | float] = {
            "projects_total": len(projects),
            "projects_active": sum(project.status == "active" for project in projects),
            "open_tasks": open_tasks,
            "blocked_tasks": blocked_tasks,
            "goals_total": len(goals),
            "goals_achieved": sum(goal.status == "achieved" for goal in goals),
            "average_goal_progress": average_progress,
            "memories_total_visible": len(memories),
            "commercial_reports_visible": len(reports),
            "campaign_templates_visible": len(campaigns),
            "alerts_total": len(alerts),
        }

        return DashboardSnapshot(
            generated_at=self._now(),
            summary=summary,
            projects=tuple(project.to_dict() for project in projects),
            goals=tuple(goal.to_dict() for goal in goals),
            priority_tasks=tuple(priority_tasks[:bounded]),
            recent_memories=tuple(memory.to_dict() for memory in memories),
            top_products=tuple(
                {
                    "id": report.id,
                    "product_name": report.product_name,
                    "marketplace": report.marketplace,
                    "profit": str(report.profit),
                    "margin_percent": str(report.margin_percent),
                    "potential_score": (
                        str(report.potential_score) if report.potential_score is not None else None
                    ),
                }
                for report in reports
            ),
            campaign_templates=tuple(
                {"id": item.id, **asdict(item.template)} for item in campaigns
            ),
            alerts=tuple(alerts[:bounded]),
        )


__all__ = ["DashboardAlert", "DashboardSnapshot", "IntelligentDashboardService"]
