"""ZeusExAI identity and status commands."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from openjarvis.zeusex import ZEUSEX_IDENTITY


@click.group(help="Comandos de identidade e diagnóstico do ZeusExAI.")
def zeusex() -> None:
    """Expose ZeusExAI-specific commands without replacing the upstream CLI."""


@zeusex.command("status")
@click.option(
    "--mode",
    type=click.Choice(
        ["assistant", "system", "vision", "sales", "monitor", "developer"],
        case_sensitive=False,
    ),
    default="assistant",
    show_default=True,
    help="Modo operacional a exibir.",
)
def status(mode: str) -> None:
    """Show the active ZeusExAI identity and operating mode."""

    identity = ZEUSEX_IDENTITY
    table = Table(title=f"{identity.name} — Sistema online")
    table.add_column("Componente", style="bold")
    table.add_column("Estado")
    table.add_row("Nome", identity.name)
    table.add_row("Chamada", identity.short_name)
    table.add_row("Idioma", identity.locale)
    table.add_row("Palavra de ativação", identity.wake_word)
    table.add_row("Modo", mode.lower())
    table.add_row("Política", "Confirmação obrigatória para ações sensíveis")

    Console().print(table)


@zeusex.command("prompt")
@click.option(
    "--mode",
    type=click.Choice(
        ["assistant", "system", "vision", "sales", "monitor", "developer"],
        case_sensitive=False,
    ),
    default="assistant",
    show_default=True,
)
def prompt(mode: str) -> None:
    """Print the system prompt generated for a ZeusExAI mode."""

    click.echo(ZEUSEX_IDENTITY.system_prompt(mode))


__all__ = ["zeusex"]
