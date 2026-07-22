"""Automação de desktop com allowlist rígida e sem shell arbitrário."""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DesktopApp:
    name: str
    commands: dict[str, tuple[str, ...]]


_ALLOWED_APPS: dict[str, DesktopApp] = {
    "calculator": DesktopApp(
        "calculator",
        {
            "Windows": ("calc.exe",),
            "Darwin": ("open", "-a", "Calculator"),
            "Linux": ("gnome-calculator",),
        },
    ),
    "text-editor": DesktopApp(
        "text-editor",
        {
            "Windows": ("notepad.exe",),
            "Darwin": ("open", "-a", "TextEdit"),
            "Linux": ("gedit",),
        },
    ),
}


def allowed_applications() -> tuple[str, ...]:
    """Retorna os identificadores permitidos para auditoria e ajuda."""

    return tuple(sorted(_ALLOWED_APPS))


def open_allowed_application(argument: str = "") -> str:
    """Abre somente um aplicativo presente na allowlist fixa.

    Não usa shell, não aceita caminhos e não concatena argumentos do usuário.
    """

    app_name = argument.strip().lower()
    app = _ALLOWED_APPS.get(app_name)
    if app is None:
        allowed = ", ".join(allowed_applications())
        return f"Aplicativo não autorizado. Permitidos: {allowed}."

    command = app.commands.get(platform.system())
    if command is None:
        return f"O aplicativo '{app_name}' não está disponível neste sistema."

    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, ValueError):
        return f"Não foi possível abrir o aplicativo '{app_name}'."
    return f"Aplicativo autorizado aberto: {app_name}."


__all__ = ["allowed_applications", "open_allowed_application"]
