"""Testes da seleção segura de motores do ZeusExAI."""

from __future__ import annotations

from openjarvis.zeusex.engines import (
    EngineSettings,
    OllamaEngine,
    OpenAICompatibleEngine,
    build_engine,
)
from openjarvis.zeusex.runtime import DisabledEngine


def test_provider_disabled_by_default() -> None:
    engine = build_engine(EngineSettings())
    assert isinstance(engine, DisabledEngine)


def test_openai_requires_model_and_key() -> None:
    without_model = build_engine(EngineSettings(provider="openai", api_key="secret"))
    without_key = build_engine(EngineSettings(provider="openai", model="gpt-test"))
    assert isinstance(without_model, DisabledEngine)
    assert isinstance(without_key, DisabledEngine)


def test_builds_openai_compatible_engine() -> None:
    engine = build_engine(
        EngineSettings(
            provider="openai-compatible",
            model="modelo-teste",
            api_key="segredo",
            base_url="http://localhost:9000/v1",
        )
    )
    assert isinstance(engine, OpenAICompatibleEngine)
    assert engine.model == "modelo-teste"
    assert engine.base_url == "http://localhost:9000/v1"


def test_builds_ollama_with_safe_local_default() -> None:
    engine = build_engine(EngineSettings(provider="ollama", model="qwen2.5:3b"))
    assert isinstance(engine, OllamaEngine)
    assert engine.base_url == "http://127.0.0.1:11434"


def test_unknown_provider_stays_disabled() -> None:
    engine = build_engine(EngineSettings(provider="unknown", model="x"))
    assert isinstance(engine, DisabledEngine)
    assert "desconhecido" in engine.reason.lower()
