"""Comandos oficiais do ZeusExAI integrados à CLI principal."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from openjarvis.zeusex import ZEUSEX_IDENTITY
from openjarvis.zeusex.diagnostics import diagnose_provider
from openjarvis.zeusex.engines import EngineSettings, build_engine
from openjarvis.zeusex.runtime import ZeusRuntime
from openjarvis.zeusex.setup_assistant import build_setup_plan
from openjarvis.zeusex.skills import default_registry

_MODES = ["assistant", "system", "vision", "sales", "monitor", "developer"]


def _runtime() -> ZeusRuntime:
    """Cria o runtime usando apenas configuração de ambiente."""

    return ZeusRuntime(engine=build_engine())


@click.group(help="Identidade, conversa, memória, diagnóstico e Skills do ZeusExAI.")
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
    table.add_row("Skills", str(len(default_registry().list())))
    table.add_row("Política", "Confirmação obrigatória para ações sensíveis")
    Console().print(table)


@zeusex.command("diagnose")
def diagnose() -> None:
    """Verifica configuração e conectividade do provedor sem expor credenciais."""

    result = diagnose_provider()
    prefix = "OK" if result.ok else "FALHA"
    click.echo(f"[{prefix}] {result.provider}: {result.message}")


@zeusex.command("setup-plan")
@click.option(
    "--provider",
    type=click.Choice(["ollama", "openai", "openai-compatible"], case_sensitive=False),
    required=True,
)
@click.option("--model", required=True, help="Modelo que será utilizado.")
@click.option("--base-url", default="", help="URL alternativa do provedor.")
@click.option(
    "--shell",
    type=click.Choice(["powershell", "cmd", "posix"], case_sensitive=False),
    default=None,
    help="Shell para o qual os comandos serão gerados.",
)
@click.option(
    "--api-key-ready",
    is_flag=True,
    help="Confirma apenas que uma chave OpenAI está disponível; a chave não é recebida.",
)
def setup_plan(
    provider: str,
    model: str,
    base_url: str,
    shell: str | None,
    api_key_ready: bool,
) -> None:
    """Gera comandos temporários de configuração sem gravar segredos."""

    try:
        plan = build_setup_plan(
            provider,
            model,
            base_url=base_url,
            api_key_supplied=api_key_ready,
            shell=shell,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(plan.render())


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


@zeusex.group("skill", help="Lista e executa Skills modulares do ZeusExAI.")
def skill_group() -> None:
    """Gerencia o catálogo local de Skills."""


@skill_group.command("list")
def skill_list() -> None:
    """Lista Skills registradas, origem e permissões declaradas."""

    table = Table(title="Skills do ZeusExAI")
    table.add_column("Nome", style="bold")
    table.add_column("Descrição")
    table.add_column("Permissões")
    table.add_column("Origem")
    table.add_column("Confirmação")
    for skill in default_registry().list():
        permissions = ", ".join(skill.permissions) if skill.permissions else "nenhuma"
        table.add_row(
            skill.name,
            skill.description,
            permissions,
            skill.source,
            "sim" if skill.requires_confirmation else "não",
        )
    Console().print(table)


@skill_group.command("manifest")
@click.argument("name")
def skill_manifest(name: str) -> None:
    """Exibe o manifesto auditável de uma Skill."""

    skill = default_registry().get(name)
    if skill is None:
        raise click.ClickException(f"Skill desconhecida: {name}.")
    manifest = skill.manifest()
    for key, value in manifest.items():
        click.echo(f"{key}: {value}")


@skill_group.command("run")
@click.argument("name")
@click.argument("argument", nargs=-1)
@click.option("--confirm", is_flag=True, help="Confirma explicitamente uma ação sensível.")
def skill_run(name: str, argument: tuple[str, ...], confirm: bool) -> None:
    """Executa uma Skill registrada."""

    click.echo(default_registry().execute(name, " ".join(argument), confirmed=confirm))


__all__ = ["zeusex"]
