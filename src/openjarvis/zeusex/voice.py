"""Fundação do módulo de voz pt-BR do ZeusExAI.

Esta etapa define configuração, palavra de ativação e normalização de comandos.
Captura de microfone e síntese permanecem adaptadores opcionais para evitar
acoplamento a bibliotecas pesadas no núcleo.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    locale: str = "pt-BR"
    wake_word: str = "Zeus"
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "VoiceConfig":
        enabled = os.getenv("ZEUSEX_VOICE_ENABLED", "false").strip().lower() in {
            "1", "true", "yes", "on", "sim",
        }
        return cls(
            locale=os.getenv("ZEUSEX_VOICE_LOCALE", "pt-BR").strip() or "pt-BR",
            wake_word=os.getenv("ZEUSEX_WAKE_WORD", "Zeus").strip() or "Zeus",
            enabled=enabled,
        )


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", plain).strip().lower()


def extract_wake_command(transcript: str, config: VoiceConfig | None = None) -> str | None:
    """Extrai o comando após a palavra de ativação, sem executar ações."""

    settings = config or VoiceConfig.from_env()
    clean = _normalize(transcript)
    wake = _normalize(settings.wake_word)
    if not clean or not wake:
        return None
    if clean == wake:
        return ""
    prefix = f"{wake} "
    if not clean.startswith(prefix):
        return None
    return clean[len(prefix):].strip()


def voice_status(config: VoiceConfig | None = None) -> str:
    settings = config or VoiceConfig.from_env()
    state = "ativado" if settings.enabled else "desativado"
    return f"Voz: {state} | Idioma: {settings.locale} | Palavra de ativação: {settings.wake_word}"


__all__ = ["VoiceConfig", "extract_wake_command", "voice_status"]
