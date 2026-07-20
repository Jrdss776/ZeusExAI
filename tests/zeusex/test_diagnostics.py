"""Testes do diagnóstico seguro de provedores do ZeusExAI."""

from openjarvis.zeusex.diagnostics import diagnose_provider
from openjarvis.zeusex.engines import EngineSettings


def test_disabled_provider_reports_inactive() -> None:
    result = diagnose_provider(EngineSettings(provider="disabled"))

    assert result.ok is False
    assert result.provider == "disabled"


def test_openai_requires_model_and_key() -> None:
    missing_model = diagnose_provider(EngineSettings(provider="openai", api_key="segredo"))
    missing_key = diagnose_provider(EngineSettings(provider="openai", model="modelo"))

    assert missing_model.ok is False
    assert "ZEUSEX_AI_MODEL" in missing_model.message
    assert missing_key.ok is False
    assert "ZEUSEX_AI_API_KEY" in missing_key.message


def test_openai_diagnostic_does_not_expose_key() -> None:
    secret = "nao-mostrar-esta-chave"
    result = diagnose_provider(
        EngineSettings(provider="openai", model="modelo", api_key=secret)
    )

    assert result.ok is True
    assert secret not in result.message
