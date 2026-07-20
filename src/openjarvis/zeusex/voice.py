"""Configuração e palavra de ativação do módulo de voz pt-BR do ZeusExAI."""

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
    capture_backend: str = "none"
    synthesizer_backend: str = "none"
    model: str = "small"
    listen_seconds: float = 5.0

    @classmethod
    def from_env(cls) -> "VoiceConfig":
        enabled = os.getenv("ZEUSEX_VOICE_ENABLED", "false").strip().lower() in {
            "1", "true", "yes", "on", "sim",
        }
        try:
            listen_seconds = float(os.getenv("ZEUSEX_VOICE_LISTEN_SECONDS", "5"))
        except ValueError:
            listen_seconds = 5.0
        return cls(
            locale=os.getenv("ZEUSEX_VOICE_LOCALE", "pt-BR").strip() or "pt-BR",
            wake_word=os.getenv("ZEUSEX_WAKE_WORD", "Zeus").strip() or "Zeus",
            enabled=enabled,
            capture_backend=os.getenv("ZEUSEX_VOICE_CAPTURE", "none").strip().lower() or "none",
            synthesizer_backend=os.getenv("ZEUSEX_VOICE_SYNTHESIZER", "none").strip().lower() or "none",
            model=os.getenv("ZEUSEX_VOICE_MODEL", "small").strip() or "small",
            listen_seconds=max(1.0, min(30.0, listen_seconds)),
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
    return (
        f"Voz: {state} | Idioma: {settings.locale} | "
        f"Palavra de ativação: {settings.wake_word} | "
        f"Captura: {settings.capture_backend} | Síntese: {settings.synthesizer_backend}"
    )


__all__ = ["VoiceConfig", "extract_wake_command", "voice_status"]
