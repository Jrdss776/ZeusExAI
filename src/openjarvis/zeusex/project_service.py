"""Serviço de projetos integrado à memória inteligente."""

from __future__ import annotations

from dataclasses import dataclass

from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.projects import Project, ProjectStore, ProjectTask


@dataclass(slots=True)
class ProjectService:
    projects: ProjectStore
    memories: IntelligentMemoryStore

    def create_project(
        self,
        name: str,
        *,
        description: str = "",
        objective: str | None = None,
        status: str = "planned",
    ) -> Project:
        project = self.projects.create_project(
            name,
            description=description,
            objective=objective,
            status=status,
        )
        summary = f"Projeto criado: {project.name}. Status: {project.status}."
        if project.objective:
            summary += f" Objetivo: {project.objective}"
        self.memories.remember(
            summary,
            category="project",
            project=project.name,
            importance=4,
        )
        return project

    def add_task(
        self,
        project_id: int,
        title: str,
        *,
        description: str = "",
        status: str = "todo",
        priority: str = "medium",
        due_at: str | None = None,
    ) -> ProjectTask:
        project = self.projects.get_project(project_id)
        task = self.projects.add_task(
            project_id,
            title,
            description=description,
            status=status,
            priority=priority,
            due_at=due_at,
        )
        if task.priority in {"high", "critical"}:
            self.memories.remember(
                f"Tarefa prioritária: {task.title}. Status: {task.status}.",
                category="project",
                project=project.name,
                importance=5 if task.priority == "critical" else 4,
            )
        return task

    def record_decision(self, project_id: int, content: str, *, importance: int = 4) -> int:
        project = self.projects.get_project(project_id)
        memory = self.memories.remember(
            content,
            category="decision",
            project=project.name,
            importance=importance,
        )
        return memory.id


__all__ = ["ProjectService"]
