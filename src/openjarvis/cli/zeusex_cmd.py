"""Comandos oficiais do ZeusExAI integrados à CLI principal."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from openjarvis.zeusex import ZEUSEX_IDENTITY
from openjarvis.zeusex.engines import EngineSettings, build_engine
from openjarvis.zeusex.runtime import ZeusRuntime

_MODES = ["assistant", "system", "vision", "sales", "monitor", "developer"]


def _runtime() -> ZeusRuntime:
    """Cria o runtime usando apenas configuração de ambiente."""

    return ZeusRuntime(engine=build_engine())


@click.group(help="Identidade, conversa, memória e diagnóstico do ZeusExAI.")
def zeusex() -> None:
    """Expõe os recursos ZeusExAI sem substituir a CLI original."""


@zeusex.command("status")
@click.option(
    "--mode",
    type=click.Choice(_MODES, case_sensitive=False),
    default="assistant",
    show_default=True,
    help="Modo operacional a exibir.",
)
def status(mode: str) -> None:
    """Exibe identidade, modo, provedor e política de segurança."""

    identity = ZEUSEX_IDENTITY
    settings = EngineSettings.from_env()
    provider = settings.provider or "disabled"
    model = settings.model or "não configurado"
    table = Table(title=f"{identity.name} — Sistema online")
    table.add_column("Componente", style="bold")
    table.add_column("Estado")
    table.add_row("Nome", identity.name)
    table.add_row("Chamada", identity.short_name)
    table.add_row("Idioma", identity.locale)
    table.add_row("Palavra de ativação", identity.wake_word)
    table.add_row("Modo", mode.lower())
    table.add_row("Memória", "SQLite local")
    table.add_row("Provedor de IA", provider)
    table.add_row("Modelo", model)
    table.add_row("Política", "Confirmação obrigatória para ações sensíveis")
    Console().print(table)


@zeusex.command("prompt")
@click.option(
    "--mode",
    type=click.Choice(_MODES, case_sensitive=False),
    default="assistant",
    show_default=True,
)
def prompt(mode: str) -> None:
    """Mostra o prompt de sistema gerado para um modo ZeusExAI."""

    click.echo(ZEUSEX_IDENTITY.system_prompt(mode))


@zeusex.command("ask")
@click.argument("message", nargs=-1, required=True)
@click.option(
    "--mode",
    type=click.Choice(_MODES, case_sensitive=False),
    default="assistant",
    show_default=True,
)
def ask(message: tuple[str, ...], mode: str) -> None:
    """Processa uma mensagem pelo runtime persistente do ZeusExAI."""

    click.echo(_runtime().handle(" ".join(message), mode=mode.lower()))


@zeusex.command("chat")
@click.option(
    "--mode",
    type=click.Choice(_MODES, case_sensitive=False),
    default="assistant",
    show_default=True,
)
def chat(mode: str) -> None:
    """Inicia uma conversa local interativa. Digite sair para encerrar."""

    runtime = _runtime()
    console = Console()
    console.print(f"[bold]{ZEUSEX_IDENTITY.name}[/bold] online. Digite 'sair' para encerrar.")
    while True:
        try:
            message = console.input("[bold cyan]Você:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nConversa encerrada.")
            break
        if message.lower() in {"sair", "exit", "quit"}:
            console.print("Conversa encerrada.")
            break
        console.print(f"[bold green]Zeus:[/bold green] {runtime.handle(message, mode=mode.lower())}")


@zeusex.command("remember")
@click.argument("content", nargs=-1, required=True)
def remember(content: tuple[str, ...]) -> None:
    """Registra uma memória persistente local."""

    click.echo(_runtime().remember(" ".join(content)))


@zeusex.command("memory")
@click.option("--limit", type=click.IntRange(1, 100), default=10, show_default=True)
def memory(limit: int) -> None:
    """Lista memórias persistentes recentes."""

    items = _runtime().memories(limit)
    if not items:
        click.echo("Nenhuma memória registrada.")
        return
    for index, item in enumerate(items, start=1):
        click.echo(f"{index}. {item}")


__all__ = ["zeusex"]
