"""Registro modular e descoberta de Skills do ZeusExAI."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import metadata
from typing import Any

SkillHandler = Callable[[str], str]
ENTRY_POINT_GROUP = "zeusex.skills"


@dataclass(frozen=True, slots=True)
class Skill:
    """Unidade funcional independente acionada por um nome curto."""

    name: str
    description: str
    handler: SkillHandler
    requires_confirmation: bool = False

    def execute(self, argument: str = "", *, confirmed: bool = False) -> str:
        if self.requires_confirmation and not confirmed:
            return f"Confirmação necessária para executar a skill '{self.name}'."
        return self.handler(argument.strip())


class SkillRegistry:
    """Catálogo extensível de Skills, desacoplado do runtime principal."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        key = skill.name.strip().lower()
        if not key:
            raise ValueError("A skill precisa de um nome.")
        if key in self._skills:
            raise ValueError(f"A skill '{key}' já está registrada.")
        self._skills[key] = skill

    def register_many(self, skills: Iterable[Skill]) -> None:
        for skill in skills:
            self.register(skill)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name.strip().lower())

    def list(self) -> list[Skill]:
        return [self._skills[key] for key in sorted(self._skills)]

    def execute(self, name: str, argument: str = "", *, confirmed: bool = False) -> str:
        skill = self.get(name)
        if skill is None:
            return f"Skill desconhecida: {name}."
        try:
            return skill.execute(argument, confirmed=confirmed)
        except Exception as exc:  # proteção na fronteira de plugins
            return f"A skill '{skill.name}' falhou: {type(exc).__name__}."


def _coerce_plugin(value: Any) -> list[Skill]:
    """Normaliza um entry point para uma ou mais Skills."""

    loaded = value() if callable(value) and not isinstance(value, Skill) else value
    if isinstance(loaded, Skill):
        return [loaded]
    if isinstance(loaded, SkillRegistry):
        return loaded.list()
    if isinstance(loaded, Iterable) and not isinstance(loaded, (str, bytes, dict)):
        skills = list(loaded)
        if all(isinstance(item, Skill) for item in skills):
            return skills
    raise TypeError("Plugin de Skill precisa fornecer Skill, SkillRegistry ou Iterable[Skill].")


def discover_skills(registry: SkillRegistry, *, group: str = ENTRY_POINT_GROUP) -> list[str]:
    """Descobre plugins instalados por entry points sem interromper a inicialização."""

    errors: list[str] = []
    entry_points = metadata.entry_points()
    selected = entry_points.select(group=group) if hasattr(entry_points, "select") else entry_points.get(group, [])
    for entry_point in selected:
        try:
            registry.register_many(_coerce_plugin(entry_point.load()))
        except Exception as exc:
            errors.append(f"{entry_point.name}: {type(exc).__name__}")
    return errors


def default_registry(*, discover_plugins: bool = True) -> SkillRegistry:
    """Cria o catálogo inicial com Skills locais e plugins opcionais."""

    registry = SkillRegistry()
    registry.register(
        Skill(
            name="echo",
            description="Repete um texto para validar o sistema de Skills.",
            handler=lambda argument: argument or "Nenhum texto informado.",
        )
    )
    registry.register(
        Skill(
            name="system-action",
            description="Ponto reservado para automações sensíveis do sistema.",
            handler=lambda argument: f"Ação autorizada: {argument or 'sem descrição'}",
            requires_confirmation=True,
        )
    )
    if discover_plugins:
        discover_skills(registry)
    return registry


__all__ = [
    "ENTRY_POINT_GROUP",
    "Skill",
    "SkillHandler",
    "SkillRegistry",
    "default_registry",
    "discover_skills",
]
