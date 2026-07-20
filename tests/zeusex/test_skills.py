"""Testes do registro modular de Skills do ZeusExAI."""

from openjarvis.zeusex.skills import Skill, SkillRegistry, default_registry


def test_registry_executes_registered_skill() -> None:
    registry = SkillRegistry()
    registry.register(Skill("upper", "Converte texto.", lambda value: value.upper()))

    assert registry.execute("upper", "zeus") == "ZEUS"


def test_sensitive_skill_requires_confirmation() -> None:
    registry = default_registry()

    blocked = registry.execute("system-action", "desligar")
    allowed = registry.execute("system-action", "desligar", confirmed=True)

    assert "Confirmação necessária" in blocked
    assert allowed == "Ação autorizada: desligar"


def test_duplicate_skill_is_rejected() -> None:
    registry = SkillRegistry()
    skill = Skill("echo", "Teste.", lambda value: value)
    registry.register(skill)

    try:
        registry.register(skill)
    except ValueError as exc:
        assert "já está registrada" in str(exc)
    else:
        raise AssertionError("Uma skill duplicada deveria ser rejeitada.")
