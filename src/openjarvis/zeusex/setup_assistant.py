"""Assistente seguro de configuração dos provedores do ZeusExAI.

O módulo apenas gera instruções e comandos de ambiente. Nenhuma chave é salva em
arquivos do repositório ou exibida novamente após a entrada do usuário.
"""

from __future__ import annotations

from dataclasses import dataclass
import platform
import shlex


@dataclass(frozen=True, slots=True)
class SetupPlan:
    """Plano auditável para configurar um provedor sem persistir segredos."""

    provider: str
    model: str
    base_url: str
    commands: tuple[str, ...]
    notes: tuple[str, ...]

    def render(self) -> str:
        lines = [
            f"Provedor: {self.provider}",
            f"Modelo: {self.model}",
            f"URL base: {self.base_url or 'padrão do provedor'}",
            "",
            "Comandos para a sessão atual:",
            *self.commands,
        ]
        if self.notes:
            lines.extend(["", "Observações:", *[f"- {note}" for note in self.notes]])
        return "\n".join(lines)


def _quote(value: str) -> str:
    return shlex.quote(value)


def _powershell_quote(value: str) -> str:
    return value.replace("`", "``").replace('"', '`"')


def build_setup_plan(
    provider: str,
    model: str,
    *,
    base_url: str = "",
    api_key_supplied: bool = False,
    shell: str | None = None,
) -> SetupPlan:
    """Gera comandos de configuração sem receber ou armazenar a chave real."""

    normalized_provider = provider.strip().lower()
    clean_model = model.strip()
    clean_base_url = base_url.strip().rstrip("/")
    selected_shell = (shell or ("powershell" if platform.system() == "Windows" else "posix")).lower()

    if normalized_provider not in {"ollama", "openai", "openai-compatible"}:
        raise ValueError("Provedor suportado: ollama, openai ou openai-compatible.")
    if not clean_model:
        raise ValueError("Informe o modelo que será utilizado.")
    if normalized_provider.startswith("openai") and not api_key_supplied:
        raise ValueError("A configuração OpenAI exige confirmação de que uma chave está disponível.")

    values = {
        "ZEUSEX_AI_PROVIDER": normalized_provider,
        "ZEUSEX_AI_MODEL": clean_model,
    }
    if clean_base_url:
        values["ZEUSEX_AI_BASE_URL"] = clean_base_url

    commands: list[str] = []
    if selected_shell in {"powershell", "pwsh"}:
        commands.extend(
            f'$env:{key} = "{_powershell_quote(value)}"'
            for key, value in values.items()
        )
        if normalized_provider.startswith("openai"):
            commands.append('$env:ZEUSEX_AI_API_KEY = "<cole-a-chave-apenas-nesta-sessao>"')
    elif selected_shell in {"cmd", "windows-cmd"}:
        commands.extend(f"set {key}={value}" for key, value in values.items())
        if normalized_provider.startswith("openai"):
            commands.append("set ZEUSEX_AI_API_KEY=<cole-a-chave-apenas-nesta-sessao>")
    else:
        commands.extend(f"export {key}={_quote(value)}" for key, value in values.items())
        if normalized_provider.startswith("openai"):
            commands.append("export ZEUSEX_AI_API_KEY='<cole-a-chave-apenas-nesta-sessao>'")

    notes = [
        "Os comandos valem apenas para a sessão atual do terminal.",
        "Substitua o marcador da chave apenas no terminal local.",
        "A chave não deve ser colocada em commits, prints ou arquivos versionados.",
        "Execute 'jarvis zeusex diagnose' após configurar.",
    ]
    if normalized_provider == "ollama":
        notes.append("Confirme que o Ollama está em execução e que o modelo já foi baixado.")

    return SetupPlan(
        provider=normalized_provider,
        model=clean_model,
        base_url=clean_base_url,
        commands=tuple(commands),
        notes=tuple(notes),
    )


__all__ = ["SetupPlan", "build_setup_plan"]
