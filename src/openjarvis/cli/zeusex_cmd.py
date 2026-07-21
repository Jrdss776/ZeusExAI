"""Comandos oficiais do ZeusExAI integrados à CLI principal."""

from __future__ import annotations

from datetime import datetime
import json

import click
from rich.console import Console
from rich.table import Table

from openjarvis.zeusex import ZEUSEX_IDENTITY
from openjarvis.zeusex.analysis_360 import analysis_360_from_mapping
from openjarvis.zeusex.analysis_queue import AnalysisQueue
from openjarvis.zeusex.analysis_worker import AnalysisWorker
from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.campaigns import CampaignTemplate, campaign_from_mapping
from openjarvis.zeusex.diagnostics import diagnose_provider
from openjarvis.zeusex.engines import EngineSettings, build_engine
from openjarvis.zeusex.marketplace_http import (
    MarketplaceHTTPError,
    MercadoLivreReadClient,
)
from openjarvis.zeusex.marketplace import (
    PotentialSignals,
    ProductInput,
    analyze_potential,
    analyze_profit,
    create_advertisement_draft,
)
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.multichannel import generate_multichannel_content
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.runtime import RuntimeConfig, ZeusRuntime
from openjarvis.zeusex.scheduler import ALLOWED_JOB_TYPES, SafeScheduler
from openjarvis.zeusex.setup_assistant import build_setup_plan
from openjarvis.zeusex.skills import default_registry
from openjarvis.zeusex.voice import VoiceConfig, voice_status
from openjarvis.zeusex.voice_backends import (
    VoiceBackendError,
    build_capture_backend,
    build_synthesizer_backend,
    list_input_devices,
)
from openjarvis.zeusex.voice_diagnostics import diagnose_voice
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


@voice_group.command("diagnose")
def voice_diagnose_command() -> None:
    """Verifica configuração e dependências sem abrir microfone."""

    for item in diagnose_voice():
        click.echo(f"[{'OK' if item.ok else 'FALHA'}] {item.component}: {item.message}")


@voice_group.command("devices")
def voice_devices_command() -> None:
    """Lista somente dispositivos com canais de entrada."""

    try:
        devices = list_input_devices()
    except VoiceBackendError as exc:
        raise click.ClickException(str(exc)) from exc
    if not devices:
        click.echo("Nenhum dispositivo de entrada disponível.")
        return
    table = Table(title="Dispositivos de entrada")
    table.add_column("ID", style="bold")
    table.add_column("Nome")
    table.add_column("Canais")
    table.add_column("Taxa padrão")
    for device in devices:
        table.add_row(
            str(device["id"]),
            str(device["name"]),
            str(device["channels"]),
            str(device["sample_rate"]),
        )
    Console().print(table)


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
        input_device=env.input_device,
        preferred_voice=env.preferred_voice,
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
            input_device=config.input_device,
        )
        synthesizer = build_synthesizer_backend(
            config.synthesizer_backend if speak else "none",
            preferred_voice=config.preferred_voice,
        )
    except VoiceBackendError as exc:
        raise click.ClickException(str(exc)) from exc

    turn = VoiceSession(
        _runtime(),
        config=config,
        capture=capture,
        synthesizer=synthesizer,
    ).listen_once(mode=mode.lower())
    click.echo(turn.response if turn.activated else turn.reason)


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


@zeusex.group("marketplace", help="Analisa produtos e cria rascunhos comerciais sem publicar.")
def marketplace_group() -> None:
    """Ferramentas locais da Fase 14 para Shopee e Mercado Livre."""


@marketplace_group.command("profit")
@click.option("--name", required=True)
@click.option(
    "--marketplace",
    type=click.Choice(["shopee", "mercado_livre"], case_sensitive=False),
    required=True,
)
@click.option("--price", required=True)
@click.option("--cost", required=True)
@click.option("--fee-percent", default="0", show_default=True)
@click.option("--fixed-fee", default="0", show_default=True)
@click.option("--shipping", default="0", show_default=True)
@click.option("--tax-percent", default="0", show_default=True)
def marketplace_profit(
    name: str,
    marketplace: str,
    price: str,
    cost: str,
    fee_percent: str,
    fixed_fee: str,
    shipping: str,
    tax_percent: str,
) -> None:
    """Calcula margem, lucro, ROI e preço de equilíbrio."""

    try:
        product = ProductInput(
            name=name,
            marketplace=marketplace,
            sale_price=price,
            product_cost=cost,
            marketplace_fee_percent=fee_percent,
            fixed_fee=fixed_fee,
            shipping_cost=shipping,
            tax_percent=tax_percent,
        )
        result = analyze_profit(product)
    except (ValueError, ArithmeticError) as exc:
        raise click.ClickException(str(exc)) from exc

    table = Table(title=f"Análise comercial — {result.product.name}")
    table.add_column("Indicador", style="bold")
    table.add_column("Resultado")
    table.add_row("Receita", f"R$ {result.revenue}")
    table.add_row("Taxa do marketplace", f"R$ {result.marketplace_fee}")
    table.add_row("Impostos", f"R$ {result.taxes}")
    table.add_row("Custos totais", f"R$ {result.total_cost}")
    table.add_row("Lucro", f"R$ {result.profit}")
    table.add_row("Margem", f"{result.margin_percent}%")
    table.add_row("ROI", f"{result.roi_percent}%")
    table.add_row("Preço de equilíbrio", f"R$ {result.break_even_price}")
    Console().print(table)


@marketplace_group.command("potential")
@click.option("--demand", required=True)
@click.option("--competition", required=True)
@click.option("--margin", required=True)
@click.option("--listing-quality", required=True)
def marketplace_potential(
    demand: str,
    competition: str,
    margin: str,
    listing_quality: str,
) -> None:
    """Pontua potencial com sinais informados, todos entre 0 e 100."""

    try:
        result = analyze_potential(
            PotentialSignals(
                demand=demand,
                competition=competition,
                margin=margin,
                listing_quality=listing_quality,
            )
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Potencial: {result.score}/100 — {result.classification}.")


@marketplace_group.command("draft")
@click.option("--name", required=True)
@click.option(
    "--marketplace",
    type=click.Choice(["shopee", "mercado_livre"], case_sensitive=False),
    required=True,
)
@click.option("--attribute", "attributes", multiple=True, help="Fato no formato chave=valor.")
def marketplace_draft(name: str, marketplace: str, attributes: tuple[str, ...]) -> None:
    """Gera um rascunho local; não publica nem completa fatos ausentes."""

    facts: dict[str, str] = {}
    for attribute in attributes:
        key, separator, value = attribute.partition("=")
        if not separator or not key.strip() or not value.strip():
            raise click.ClickException("Use --attribute no formato chave=valor.")
        facts[key.strip()] = value.strip()
    try:
        draft = create_advertisement_draft(name, facts, marketplace=marketplace)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Título: {draft.title}")
    for bullet in draft.bullets:
        click.echo(f"- {bullet}")
    click.echo(f"Descrição: {draft.description}")


def _analysis_queue() -> AnalysisQueue:
    return AnalysisQueue(RuntimeConfig.from_env().data_dir / "marketplace-queue.db")


def _report_store() -> AnalysisReportStore:
    return AnalysisReportStore(RuntimeConfig.from_env().data_dir / "marketplace-reports.db")


def _campaign_template_store() -> CampaignTemplateStore:
    return CampaignTemplateStore(
        RuntimeConfig.from_env().data_dir / "campaign-templates.db"
    )


def _safe_scheduler() -> SafeScheduler:
    return SafeScheduler(RuntimeConfig.from_env().data_dir / "schedules.db")


def _mobile_api_service() -> MobileAPIService:
    return MobileAPIService(
        _report_store(),
        _campaign_template_store(),
        _safe_scheduler(),
    )


@marketplace_group.command("fetch-ml")
@click.argument("listing_id")
def marketplace_fetch_ml(listing_id: str) -> None:
    """Consulta um anúncio público do Mercado Livre sem alterá-lo."""

    try:
        listing = MercadoLivreReadClient.create().fetch_listing(listing_id)
    except (ValueError, MarketplaceHTTPError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"ID: {listing.listing_id}")
    click.echo(f"Título: {listing.title}")
    click.echo(f"Preço: R$ {listing.price}")
    click.echo(
        f"Vendas informadas: {listing.sold_count}"
        if listing.sold_count is not None
        else "Vendas informadas: desconhecidas"
    )
    click.echo(f"URL: {listing.url or 'não informada'}")


@marketplace_group.group("queue", help="Gerencia a fila local de análises comerciais.")
def marketplace_queue_group() -> None:
    """Fila persistente; nenhum comando publica anúncios."""


@marketplace_queue_group.command("add")
@click.option(
    "--marketplace",
    type=click.Choice(["shopee", "mercado_livre"], case_sensitive=False),
    required=True,
)
@click.option("--payload", required=True, help="Objeto JSON com os dados da consulta.")
def marketplace_queue_add(marketplace: str, payload: str) -> None:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise click.ClickException("O payload precisa ser um objeto JSON válido.") from exc
    if not isinstance(decoded, dict):
        raise click.ClickException("O payload precisa ser um objeto JSON.")
    job = _analysis_queue().enqueue(marketplace, decoded)
    click.echo(f"Trabalho {job.id} adicionado: {job.marketplace} — {job.status}.")


@marketplace_queue_group.command("list")
@click.option(
    "--status",
    type=click.Choice(["queued", "processing", "completed", "failed"]),
    default=None,
)
@click.option("--limit", type=click.IntRange(1, 1000), default=100, show_default=True)
def marketplace_queue_list(status: str | None, limit: int) -> None:
    jobs = _analysis_queue().list(status=status, limit=limit)
    if not jobs:
        click.echo("Fila vazia.")
        return
    table = Table(title="Fila comercial do ZeusEXai")
    table.add_column("ID", style="bold")
    table.add_column("Marketplace")
    table.add_column("Status")
    table.add_column("Tentativas")
    table.add_column("Erro")
    for job in jobs:
        table.add_row(
            str(job.id),
            job.marketplace,
            job.status,
            str(job.attempts),
            job.error or "",
        )
    Console().print(table)


@marketplace_queue_group.command("run-one")
def marketplace_queue_run_one() -> None:
    """Processa um trabalho Mercado Livre; outros ficam em falha controlada."""

    client = MercadoLivreReadClient.create()

    def handle_mercado_livre(payload: dict[str, object]) -> object:
        listing_id = str(payload.get("listing_id") or payload.get("id") or "")
        if not listing_id:
            raise ValueError("Informe listing_id ou id.")
        return client.fetch_listing(listing_id)

    outcome = AnalysisWorker(
        _analysis_queue(),
        {"mercado_livre": handle_mercado_livre},
    ).run_once()
    if not outcome.processed or outcome.job is None:
        click.echo("Fila vazia.")
        return
    click.echo(
        f"Trabalho {outcome.job.id}: {outcome.job.status}"
        + (f" — {outcome.job.error}" if outcome.job.error else "")
        + "."
    )


@marketplace_group.command("analyze360")
@click.option("--payload", required=True, help="Objeto JSON com produto e dados opcionais.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
)
@click.option("--save", is_flag=True, help="Salva o relatório no histórico SQLite local.")
def marketplace_analyze360(payload: str, output_format: str, save: bool) -> None:
    """Gera uma Análise 360 local sem publicar ou buscar dados ausentes."""

    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise click.ClickException("O payload precisa ser um objeto JSON válido.") from exc
    if not isinstance(decoded, dict):
        raise click.ClickException("O payload precisa ser um objeto JSON.")
    try:
        report = analysis_360_from_mapping(decoded)
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(report.to_json() if output_format == "json" else report.to_markdown())
    if save:
        saved = _report_store().save(report)
        click.echo(f"Relatório salvo com ID {saved.id}.", err=True)


@marketplace_group.group("reports", help="Consulta o histórico local de Análises 360.")
def marketplace_reports_group() -> None:
    """Histórico local sem credenciais ou publicação externa."""


@marketplace_reports_group.command("list")
@click.option("--limit", type=click.IntRange(1, 1000), default=100, show_default=True)
def marketplace_reports_list(limit: int) -> None:
    reports = _report_store().list(limit=limit)
    if not reports:
        click.echo("Nenhum relatório salvo.")
        return
    table = Table(title="Histórico de Análises 360")
    table.add_column("ID", style="bold")
    table.add_column("Produto")
    table.add_column("Marketplace")
    table.add_column("Lucro")
    table.add_column("Margem")
    table.add_column("Potencial")
    for report in reports:
        table.add_row(
            str(report.id),
            report.product_name,
            report.marketplace,
            f"R$ {report.profit}",
            f"{report.margin_percent}%",
            str(report.potential_score) if report.potential_score is not None else "não informado",
        )
    Console().print(table)


@marketplace_reports_group.command("top")
@click.option("--limit", type=click.IntRange(1, 100), default=10, show_default=True)
@click.option("--include-unprofitable", is_flag=True)
def marketplace_reports_top(limit: int, include_unprofitable: bool) -> None:
    reports = _report_store().top_products(
        limit=limit,
        profitable_only=not include_unprofitable,
    )
    if not reports:
        click.echo("Nenhum produto disponível para o ranking.")
        return
    for index, report in enumerate(reports, start=1):
        score = (
            str(report.potential_score)
            if report.potential_score is not None
            else "não informado"
        )
        click.echo(
            f"{index}. {report.product_name} — potencial {score} — lucro R$ {report.profit}"
        )


@marketplace_reports_group.command("show")
@click.argument("report_id", type=click.IntRange(1))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
)
def marketplace_reports_show(report_id: int, output_format: str) -> None:
    report = _report_store().get(report_id)
    if report is None:
        raise click.ClickException(f"Relatório não encontrado: {report_id}.")
    click.echo(
        json.dumps(report.report, ensure_ascii=False, indent=2, sort_keys=True)
        if output_format == "json"
        else report.markdown
    )


@marketplace_group.command("content")
@click.option("--payload", required=True, help="Objeto JSON aceito pela Análise 360.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
)
@click.option("--include-price/--omit-price", default=True, show_default=True)
def marketplace_content(
    payload: str,
    output_format: str,
    include_price: bool,
) -> None:
    """Gera conteúdo para marketplaces, redes sociais e vídeos."""

    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise click.ClickException("O payload precisa ser um objeto JSON válido.") from exc
    if not isinstance(decoded, dict):
        raise click.ClickException("O payload precisa ser um objeto JSON.")
    try:
        report = analysis_360_from_mapping(decoded)
        package = generate_multichannel_content(
            report,
            include_price=include_price,
        )
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        package.to_json()
        if output_format == "json"
        else package.to_markdown()
    )


@marketplace_group.command("campaign")
@click.option(
    "--preset",
    type=click.Choice(["achadinhos-jr"], case_sensitive=False),
    default="achadinhos-jr",
    show_default=True,
)
@click.option("--payload", required=True, help="Análise 360 e catálogo opcional em JSON.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
)
def marketplace_campaign(
    preset: str,
    payload: str,
    output_format: str,
) -> None:
    """Gera campanha reutilizável sem publicar conteúdo."""

    del preset
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise click.ClickException("O payload precisa ser um objeto JSON válido.") from exc
    if not isinstance(decoded, dict):
        raise click.ClickException("O payload precisa ser um objeto JSON.")
    try:
        package = campaign_from_mapping(decoded)
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        package.to_json()
        if output_format == "json"
        else package.to_markdown()
    )


@marketplace_group.group(
    "templates",
    help="Gerencia modelos locais reutilizáveis de campanha.",
)
def marketplace_templates_group() -> None:
    """Biblioteca editorial sem credenciais."""


@marketplace_templates_group.command("save")
@click.option("--name", required=True)
@click.option("--brand", required=True)
@click.option("--call-to-action", required=True)
@click.option("--include-price/--omit-price", default=True, show_default=True)
def marketplace_templates_save(
    name: str,
    brand: str,
    call_to_action: str,
    include_price: bool,
) -> None:
    try:
        saved = _campaign_template_store().save(
            CampaignTemplate(
                name=name,
                brand=brand,
                call_to_action=call_to_action,
                include_price=include_price,
            )
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Modelo {saved.template.name} salvo com ID {saved.id}.")


@marketplace_templates_group.command("list")
def marketplace_templates_list() -> None:
    templates = _campaign_template_store().list()
    if not templates:
        click.echo("Nenhum modelo salvo.")
        return
    for item in templates:
        click.echo(
            f"{item.id}. {item.template.name} — {item.template.brand} — "
            f"preço: {'sim' if item.template.include_price else 'não'}"
        )


@zeusex.group("schedule", help="Agenda somente tarefas locais permitidas.")
def schedule_group() -> None:
    """Agendador sem shell e sem publicação automática."""


@schedule_group.command("add")
@click.option(
    "--type",
    "job_type",
    type=click.Choice(sorted(ALLOWED_JOB_TYPES)),
    required=True,
)
@click.option("--at", "scheduled_at", required=True, help="Data ISO 8601 com fuso.")
@click.option("--payload", required=True, help="Objeto JSON da tarefa.")
def schedule_add(job_type: str, scheduled_at: str, payload: str) -> None:
    try:
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            raise ValueError("O payload precisa ser um objeto JSON.")
        when = datetime.fromisoformat(scheduled_at)
        task = _safe_scheduler().schedule(job_type, decoded, when)
    except (json.JSONDecodeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Agendamento {task.id}: {task.job_type} — {task.status}.")


@schedule_group.command("list")
@click.option(
    "--status",
    type=click.Choice(["pending", "running", "completed", "failed"]),
    default=None,
)
def schedule_list(status: str | None) -> None:
    tasks = _safe_scheduler().list(status=status)
    if not tasks:
        click.echo("Nenhum agendamento.")
        return
    for task in tasks:
        click.echo(
            f"{task.id}. {task.job_type} — {task.scheduled_for} — {task.status}"
        )


@zeusex.command("mobile-api")
@click.argument("method", type=click.Choice(["GET", "POST"], case_sensitive=False))
@click.argument("path")
@click.option("--body", default="{}", show_default=True)
def mobile_api_command(method: str, path: str, body: str) -> None:
    """Testa a camada Android local sem iniciar servidor de rede."""

    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise click.ClickException("O corpo precisa ser um objeto JSON válido.") from exc
    if not isinstance(decoded, dict):
        raise click.ClickException("O corpo precisa ser um objeto JSON.")
    response = _mobile_api_service().dispatch(method, path, decoded)
    click.echo(
        json.dumps(
            {"status": response.status, **response.body},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


__all__ = ["zeusex"]
