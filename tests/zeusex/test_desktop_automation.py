"""Testes da automação de desktop com allowlist."""

from openjarvis.zeusex.desktop_automation import allowed_applications, open_allowed_application
from openjarvis.zeusex.skills import default_registry


def test_desktop_allowlist_is_explicit() -> None:
    assert allowed_applications() == ("calculator", "text-editor")


def test_unknown_desktop_application_is_rejected() -> None:
    response = open_allowed_application("powershell")

    assert "não autorizado" in response
    assert "powershell" not in response


def test_open_app_skill_requires_confirmation() -> None:
    registry = default_registry(discover_plugins=False)

    blocked = registry.execute("open-app", "calculator")

    assert "Confirmação necessária" in blocked
