"""Registro modular de Skills do ZeusExAI."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

SkillHandler = Callable[[str], str]


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
    """Catálogo extensível de Skills, sem acoplamento ao runtime principal."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        key = skill.name.strip().lower()
        if not key:
            raise ValueError("A skill precisa de um nome.")
        if key in self._skills:
            raise ValueError(f"A skill '{key}' já está registrada.")
        self._skills[key] = skill

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name.strip().lower())

    def list(self) -> list[Skill]:
        return [self._skills[key] for key in sorted(self._skills)]

    def execute(self, name: str, argument: str = "", *, confirmed: bool = False) -> str:
        skill = self.get(name)
        if skill is None:
            return f"Skill desconhecida: {name}."
        return skill.execute(argument, confirmed=confirmed)


def default_registry() -> SkillRegistry:
    """Cria o catálogo inicial com Skills locais e seguras."""

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
    return registry


__all__ = ["Skill", "SkillHandler", "SkillRegistry", "default_registry"]
