"""Testes do assistente seguro de configuração."""

import pytest

from openjarvis.zeusex.setup_assistant import build_setup_plan


def test_ollama_plan_for_powershell() -> None:
    plan = build_setup_plan("ollama", "qwen2.5:3b", shell="powershell")
    rendered = plan.render()

    assert '$env:ZEUSEX_AI_PROVIDER = "ollama"' in rendered
    assert '$env:ZEUSEX_AI_MODEL = "qwen2.5:3b"' in rendered
    assert "ZEUSEX_AI_API_KEY" not in rendered


def test_openai_plan_never_receives_real_key() -> None:
    plan = build_setup_plan(
        "openai",
        "modelo-teste",
        api_key_supplied=True,
        shell="posix",
    )
    rendered = plan.render()

    assert "<cole-a-chave-apenas-nesta-sessao>" in rendered
    assert "api_key_supplied" not in rendered


def test_openai_requires_key_confirmation() -> None:
    with pytest.raises(ValueError, match="chave"):
        build_setup_plan("openai", "modelo-teste", shell="posix")


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="Provedor suportado"):
        build_setup_plan("desconhecido", "modelo", shell="posix")
