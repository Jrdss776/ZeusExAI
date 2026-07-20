"""Testes da política granular de permissões."""

from openjarvis.zeusex.permissions import PermissionPolicy
from openjarvis.zeusex.skills import Skill, SkillRegistry


def test_unknown_permission_is_denied() -> None:
    registry = SkillRegistry()
    registry.register(
        Skill(
            "network-write",
            "Teste de permissão desconhecida.",
            lambda value: value,
            permissions=("network.write",),
            source="plugin:test",
        )
    )

    response = registry.execute("network-write", "segredo", confirmed=True)

    assert response == "Permissão não autorizada: network.write."
    assert "segredo" not in response


def test_elevated_permission_requires_confirmation() -> None:
    policy = PermissionPolicy()

    blocked = policy.evaluate(("filesystem.read_directory",), confirmed=False)
    allowed = policy.evaluate(("filesystem.read_directory",), confirmed=True)

    assert blocked.allowed is False
    assert "Confirmação necessária" in blocked.reason
    assert allowed.allowed is True
