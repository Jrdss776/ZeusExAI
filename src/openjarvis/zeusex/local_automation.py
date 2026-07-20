"""Automações locais seguras e sem execução arbitrária de shell."""

from __future__ import annotations

from pathlib import Path
import platform
import sys


def system_information(_: str = "") -> str:
    """Retorna informações básicas do ambiente sem coletar dados pessoais."""

    return (
        f"Sistema: {platform.system()} {platform.release()} | "
        f"Arquitetura: {platform.machine() or 'desconhecida'} | "
        f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )


def list_local_files(argument: str = "") -> str:
    """Lista arquivos de um diretório local após confirmação no nível da Skill.

    A função não executa comandos de shell, não segue recursivamente subdiretórios e
    limita a resposta para evitar exposição excessiva de dados.
    """

    requested = Path(argument.strip() or ".").expanduser()
    try:
        directory = requested.resolve(strict=True)
    except (OSError, RuntimeError):
        return "Diretório não encontrado ou inacessível."
    if not directory.is_dir():
        return "O caminho informado não é um diretório."

    try:
        entries = sorted(directory.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    except OSError:
        return "Não foi possível acessar o diretório informado."

    visible = entries[:50]
    rendered = [f"[DIR] {item.name}" if item.is_dir() else item.name for item in visible]
    if len(entries) > len(visible):
        rendered.append(f"... e mais {len(entries) - len(visible)} item(ns).")
    return "\n".join(rendered) if rendered else "Diretório vazio."


__all__ = ["list_local_files", "system_information"]
