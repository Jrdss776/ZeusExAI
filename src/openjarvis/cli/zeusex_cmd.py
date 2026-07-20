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
from openjarvis.zeusex.voice import VoiceConfig, voice_status
from openjarvis.zeusex.voice_backends import (
    VoiceBackendError,
    build_capture_backend,
    build_synthesizer_backend,
)
from openjarvis.zeusex.voice_runtime import VoiceSession

_MODES = ["assistant", "system", "vision", "sales", "monitor", "developer"]


def _runtime() -> ZeusRuntime:
    return ZeusRuntime(engine=build_engine())


@click.group(help="Identidade, conversa, memória, diagnóstico, voz e Skills do ZeusExAI.")
def zeusex() -> None:
    """Expõe os recursos ZeusExAI sem substituir a CLI original."""


@zeusex.command("status")
@click.option("--mode", type=click.Choice(_MODES, case_sensitive=False), default="assistant", show_default=True)
def status(mode: str) -> None:
    identity = ZEUSEX_IDENTITY
    settings = EngineSettings.from_env()
    table = Table(title=f"{identity.name} — Sistema online")
    table.add_column("Componente", style="bold")
    table.add_column("Estado")
    table.add_row("Nome", identity.name)
    table.add_row("Chamada", identity.short_name)
    table.add_row("Idioma", identity.locale)
    table.add_row("Palavra de ativação", identity.wake_word)
    table.add_row("Modo", mode.lower())
    table.add_row("Memória", "SQLite local")
    table.add_row("Provedor de IA", settings.provider or "disabled")
    table.add_row("Modelo", settings.model or "não configurado")
    table.add_row("Voz", voice_status())
    table.add_row("Skills", str(len(default_registry().list())))
    table.add_row("Política", "Confirmação obrigatória para ações sensíveis")
    Console().print(table)


@zeusex.command("diagnose")
def diagnose() -> None:
    result = diagnose_provider()
    click.echo(f"[{'OK' if result.ok else 'FALHA'}] {result.provider}: {result.message}")


@zeusex.command("setup-plan")
@click.option("--provider", type=click.Choice(["ollama", "openai", "openai-compatible"], case_sensitive=False), required=True)
@click.option("--model", required=True)
@click.option("--base-url", default="")
@click.option("--shell", type=click.Choice(["powershell", "cmd", "posix"], case_sensitive=False), default=None)
@click.option("--api-key-ready", is_flag=True)
def setup_plan(provider: str, model: str, base_url: str, shell: str | None, api_key_ready: bool) -> None:
    try:
        plan = build_setup_plan(provider, model, base_url=base_url, api_key_supplied=api_key_ready, shell=shell)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(plan.render())


@zeusex.group("voice", help="Inspeciona, simula e executa o fluxo seguro de voz pt-BR.")
def voice_group() -> None:
    """Gerencia voz sem ativar microfone automaticamente."""


@voice_group.command("status")
def voice_status_command() -> None:
    click.echo(voice_status())


@voice_group.command("simulate")
@click.argument("transcript", nargs=-1, required=True)
@click.option("--mode", type=click.Choice(_MODES, case_sensitive=False), default="assistant", show_default=True)
@click.option("--enabled/--disabled", default=True, show_default=True)
def voice_simulate(transcript: tuple[str, ...], mode: str, enabled: bool) -> None:
    env = VoiceConfig.from_env()
    config = VoiceConfig(
        locale=env.locale,
        wake_word=env.wake_word,
        enabled=enabled,
        capture_backend=env.capture_backend,
        synthesizer_backend="none",
        model=env.model,
        listen_seconds=env.listen_seconds,
    )
    turn = VoiceSession(_runtime(), config=config).process_transcript(" ".join(transcript), mode=mode.lower())
    click.echo(turn.response if turn.activated else turn.reason)


@voice_group.command("listen")
@click.option("--mode", type=click.Choice(_MODES, case_sensitive=False), default="assistant", show_default=True)
@click.option("--speak/--no-speak", default=True, show_default=True)
def voice_listen(mode: str, speak: bool) -> None:
    """Escuta uma única fala após comando explícito do usuário."""

    config = VoiceConfig.from_env()
    if not config.enabled:
        raise click.ClickException("A voz está desativada. Defina ZEUSEX_VOICE_ENABLED=true.")
    try:
        capture = build_capture_backend(
            config.capture_backend,
            model_name=config.model,
            duration_seconds=config.listen_seconds,
        )
        synthesizer = build_synthesizer_backend(
            config.synthesizer_backend if speak else "none"
        )
    except VoiceBackendError as exc:
        raise click.ClickException(str(exc)) from exc

    turn = VoiceSession(
        _runtime(),
        config=config,
        capture=capture,
        synthesizer=synthesizer,
    ).listen_once(mode=mode.lower())
    if turn.activated:
        click.echo(turn.response or turn.reason)
    else:
        click.echo(turn.reason)


@zeusex.command("prompt")
@click.option("--mode", type=click.Choice(_MODES, case_sensitive=False), default="assistant", show_default=True)
def prompt(mode: str) -> None:
    click.echo(ZEUSEX_IDENTITY.system_prompt(mode))


@zeusex.command("ask")
@click.argument("message", nargs=-1, required=True)
@click.option("--mode", type=click.Choice(_MODES, case_sensitive=False), default="assistant", show_default=True)
def ask(message: tuple[str, ...], mode: str) -> None:
    click.echo(_runtime().handle(" ".join(message), mode=mode.lower()))


@zeusex.command("chat")
@click.option("--mode", type=click.Choice(_MODES, case_sensitive=False), default="assistant", show_default=True)
def chat(mode: str) -> None:
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
    click.echo(_runtime().remember(" ".join(content)))


@zeusex.command("memory")
@click.option("--limit", type=click.IntRange(1, 100), default=10, show_default=True)
def memory(limit: int) -> None:
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
    table = Table(title="Skills do ZeusExAI")
    table.add_column("Nome", style="bold")
    table.add_column("Descrição")
    table.add_column("Permissões")
    table.add_column("Origem")
    table.add_column("Confirmação")
    for skill in default_registry().list():
        table.add_row(
            skill.name,
            skill.description,
            ", ".join(skill.permissions) or "nenhuma",
            skill.source,
            "sim" if skill.requires_confirmation else "não",
        )
    Console().print(table)


@skill_group.command("manifest")
@click.argument("name")
def skill_manifest(name: str) -> None:
    skill = default_registry().get(name)
    if skill is None:
        raise click.ClickException(f"Skill desconhecida: {name}.")
    for key, value in skill.manifest().items():
        click.echo(f"{key}: {value}")


@skill_group.command("run")
@click.argument("name")
@click.argument("argument", nargs=-1)
@click.option("--confirm", is_flag=True)
def skill_run(name: str, argument: tuple[str, ...], confirm: bool) -> None:
    click.echo(default_registry().execute(name, " ".join(argument), confirmed=confirm))


__all__ = ["zeusex"]
