"""Serviço de objetivos integrado a projetos e memória inteligente."""

from __future__ import annotations

from dataclasses import dataclass

from openjarvis.zeusex.goals import Goal, GoalCheckIn, GoalStore
from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.projects import ProjectStore


@dataclass(slots=True)
class GoalService:
    goals: GoalStore
    projects: ProjectStore
    memories: IntelligentMemoryStore

    def create_goal(
        self,
        title: str,
        *,
        metric: str,
        target: float,
        baseline: float = 0,
        current: float | None = None,
        project_id: int | None = None,
        description: str = "",
        direction: str = "increase",
        unit: str = "",
        status: str = "planned",
        due_at: str | None = None,
    ) -> Goal:
        project_name = None
        if project_id is not None:
            project_name = self.projects.get_project(project_id).name
        goal = self.goals.create_goal(
            title,
            metric=metric,
            target=target,
            baseline=baseline,
            current=current,
            project_id=project_id,
            description=description,
            direction=direction,
            unit=unit,
            status=status,
            due_at=due_at,
        )
        self.memories.remember(
            f"Objetivo criado: {goal.title}. Métrica: {goal.metric}. Meta: {goal.target} {goal.unit}.",
            category="project" if project_name else "general",
            project=project_name,
            importance=4,
        )
        return goal

    def check_in(self, goal_id: int, value: float, *, note: str = "") -> GoalCheckIn:
        goal_before = self.goals.get_goal(goal_id)
        checkin = self.goals.check_in(goal_id, value, note=note)
        goal_after = self.goals.get_goal(goal_id)
        project_name = None
        if goal_after.project_id is not None:
            project_name = self.projects.get_project(goal_after.project_id).name
        milestone = goal_after.progress_percent >= 100 and goal_before.progress_percent < 100
        if milestone:
            self.goals.update_status(goal_id, "achieved")
        if milestone or note.strip():
            message = (
                f"Progresso do objetivo {goal_after.title}: {goal_after.current} {goal_after.unit} "
                f"({goal_after.progress_percent}%)."
            )
            if note.strip():
                message += f" Nota: {note.strip()}"
            self.memories.remember(
                message,
                category="decision" if milestone else "project",
                project=project_name,
                importance=5 if milestone else 3,
            )
        return checkin

    def summary(self, goal_id: int) -> dict[str, object]:
        goal = self.goals.get_goal(goal_id)
        return {
            "goal": goal.to_dict(),
            "checkins": [item.to_dict() for item in self.goals.list_checkins(goal_id)],
        }


__all__ = ["GoalService"]
