"""Testes do registro modular de Skills do ZeusExAI."""

from openjarvis.zeusex.skills import Skill, SkillRegistry, default_registry


def test_registry_executes_registered_skill() -> None:
    registry = SkillRegistry()
    registry.register(Skill("upper", "Converte texto.", lambda value: value.upper()))

    assert registry.execute("upper", "zeus") == "ZEUS"


def test_sensitive_skill_requires_confirmation() -> None:
    registry = default_registry(discover_plugins=False)

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


def test_plugin_failure_is_contained() -> None:
    registry = SkillRegistry()

    def fail(value: str) -> str:
        raise RuntimeError(value)

    registry.register(Skill("broken", "Falha controlada.", fail))
    response = registry.execute("broken", "segredo")

    assert response == "A skill 'broken' falhou: RuntimeError."
    assert "segredo" not in response


def test_register_many_adds_multiple_skills() -> None:
    registry = SkillRegistry()
    registry.register_many(
        [
            Skill("one", "Primeira.", lambda value: value),
            Skill("two", "Segunda.", lambda value: value),
        ]
    )

    assert [skill.name for skill in registry.list()] == ["one", "two"]
