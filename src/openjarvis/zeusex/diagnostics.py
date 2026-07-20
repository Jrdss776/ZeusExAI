"""Diagnóstico seguro dos provedores de IA do ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from openjarvis.zeusex.engines import EngineSettings


@dataclass(frozen=True, slots=True)
class DiagnosticResult:
    """Resultado normalizado de uma verificação de provedor."""

    ok: bool
    provider: str
    message: str


def diagnose_provider(settings: EngineSettings | None = None) -> DiagnosticResult:
    """Verifica configuração e conectividade sem enviar prompts ou expor segredos."""

    config = settings or EngineSettings.from_env()
    provider = config.provider or "disabled"

    if provider in {"", "disabled", "none", "off"}:
        return DiagnosticResult(False, "disabled", "Nenhum provedor de IA está ativo.")

    if provider in {"openai", "openai-compatible", "compatible"}:
        if not config.model:
            return DiagnosticResult(False, provider, "ZEUSEX_AI_MODEL não foi configurado.")
        if not config.api_key:
            return DiagnosticResult(False, provider, "ZEUSEX_AI_API_KEY não foi configurada.")
        return DiagnosticResult(
            True,
            provider,
            "Configuração válida. A credencial não foi exibida nem transmitida no diagnóstico local.",
        )

    if provider == "ollama":
        if not config.model:
            return DiagnosticResult(False, provider, "ZEUSEX_AI_MODEL não foi configurado para o Ollama.")
        base_url = config.base_url or "http://127.0.0.1:11434"
        try:
            with httpx.Client(timeout=min(config.timeout_seconds, 10.0)) as client:
                response = client.get(f"{base_url.rstrip('/')}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return DiagnosticResult(False, provider, f"Ollama indisponível: {exc.__class__.__name__}.")

        models = {
            str(item.get("name", ""))
            for item in payload.get("models", [])
            if isinstance(item, dict)
        }
        if config.model not in models:
            return DiagnosticResult(
                False,
                provider,
                f"Ollama respondeu, mas o modelo '{config.model}' não está instalado.",
            )
        return DiagnosticResult(True, provider, f"Ollama online com o modelo '{config.model}'.")

    return DiagnosticResult(False, provider, f"Provedor desconhecido: {provider}.")


__all__ = ["DiagnosticResult", "diagnose_provider"]
