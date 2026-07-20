"""Diagnóstico seguro e sem captura automática dos backends de voz."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec

from openjarvis.zeusex.voice import VoiceConfig


@dataclass(frozen=True, slots=True)
class VoiceDiagnostic:
    component: str
    ok: bool
    message: str


def _module_available(name: str) -> bool:
    return find_spec(name) is not None


def diagnose_voice(config: VoiceConfig | None = None) -> list[VoiceDiagnostic]:
    """Verifica configuração e dependências sem abrir microfone ou emitir áudio."""

    settings = config or VoiceConfig.from_env()
    results = [
        VoiceDiagnostic("config", True, f"Idioma {settings.locale}; ativação {settings.wake_word}."),
    ]

    capture = settings.capture_backend
    if capture in {"", "none", "null", "disabled"}:
        results.append(VoiceDiagnostic("captura", True, "Captura desativada."))
    elif capture in {"faster-whisper", "whisper"}:
        missing = [name for name in ("faster_whisper", "sounddevice") if not _module_available(name)]
        results.append(
            VoiceDiagnostic(
                "captura",
                not missing,
                "Backend disponível." if not missing else f"Dependências ausentes: {', '.join(missing)}.",
            )
        )
    else:
        results.append(VoiceDiagnostic("captura", False, f"Backend desconhecido: {capture}."))

    synth = settings.synthesizer_backend
    if synth in {"", "none", "null", "disabled"}:
        results.append(VoiceDiagnostic("síntese", True, "Síntese desativada."))
    elif synth in {"pyttsx3", "local"}:
        available = _module_available("pyttsx3")
        results.append(
            VoiceDiagnostic(
                "síntese",
                available,
                "Backend disponível." if available else "Dependência ausente: pyttsx3.",
            )
        )
    else:
        results.append(VoiceDiagnostic("síntese", False, f"Backend desconhecido: {synth}."))

    return results


__all__ = ["VoiceDiagnostic", "diagnose_voice"]
