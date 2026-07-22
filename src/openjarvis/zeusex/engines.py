"""Motores de IA configuráveis do ZeusExAI.

Nenhuma credencial é gravada no repositório. A seleção do provedor é feita por
variáveis de ambiente e o padrão permanece desativado por segurança.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import httpx

from openjarvis.zeusex.runtime import AIEngine, DisabledEngine


@dataclass(frozen=True, slots=True)
class EngineSettings:
    """Configuração segura para seleção do motor de IA."""

    provider: str = "disabled"
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    timeout_seconds: float = 60.0

    @classmethod
    def from_env(cls) -> "EngineSettings":
        provider = os.getenv("ZEUSEX_AI_PROVIDER", "disabled").strip().lower()
        model = os.getenv("ZEUSEX_AI_MODEL", "").strip()
        api_key = os.getenv("ZEUSEX_AI_API_KEY", "").strip()
        base_url = os.getenv("ZEUSEX_AI_BASE_URL", "").strip().rstrip("/")
        timeout = float(os.getenv("ZEUSEX_AI_TIMEOUT", "60"))
        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=max(1.0, timeout),
        )


@dataclass(slots=True)
class OpenAICompatibleEngine:
    """Motor para OpenAI e servidores compatíveis com a API Chat Completions."""

    model: str
    api_key: str
    base_url: str = ""
    timeout_seconds: float = 60.0

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        from openai import OpenAI

        kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout_seconds,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = OpenAI(**kwargs)
        messages = [
            {"role": role if role in {"system", "user", "assistant"} else "user", "content": content}
            for role, content in history
        ]
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=self.model, messages=messages)
        content = response.choices[0].message.content
        return content or ""


@dataclass(slots=True)
class OllamaEngine:
    """Motor local usando a API HTTP nativa do Ollama."""

    model: str
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 120.0

    def generate(self, prompt: str, history: list[tuple[str, str]]) -> str:
        messages = [
            {"role": role if role in {"system", "user", "assistant"} else "user", "content": content}
            for role, content in history
        ]
        messages.append({"role": "user", "content": prompt})
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url.rstrip('/')}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            payload = response.json()
        return str(payload.get("message", {}).get("content", ""))


def build_engine(settings: EngineSettings | None = None) -> AIEngine:
    """Cria o motor configurado sem expor credenciais em logs ou mensagens."""

    config = settings or EngineSettings.from_env()
    if config.provider in {"", "disabled", "none", "off"}:
        return DisabledEngine()
    if config.provider in {"openai", "openai-compatible", "compatible"}:
        if not config.model:
            return DisabledEngine("ZEUSEX_AI_MODEL não foi configurado.")
        if not config.api_key:
            return DisabledEngine("ZEUSEX_AI_API_KEY não foi configurada.")
        return OpenAICompatibleEngine(
            model=config.model,
            api_key=config.api_key,
            base_url=config.base_url,
            timeout_seconds=config.timeout_seconds,
        )
    if config.provider == "ollama":
        if not config.model:
            return DisabledEngine("ZEUSEX_AI_MODEL não foi configurado para o Ollama.")
        return OllamaEngine(
            model=config.model,
            base_url=config.base_url or "http://127.0.0.1:11434",
            timeout_seconds=config.timeout_seconds,
        )
    return DisabledEngine(f"Provedor desconhecido: {config.provider}.")


__all__ = [
    "EngineSettings",
    "OllamaEngine",
    "OpenAICompatibleEngine",
    "build_engine",
]
