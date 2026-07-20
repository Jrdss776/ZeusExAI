"""Adaptadores opcionais e sessão segura de voz do ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from openjarvis.zeusex.runtime import ZeusRuntime
from openjarvis.zeusex.voice import VoiceConfig, extract_wake_command


class SpeechCapture(Protocol):
    def listen(self, *, locale: str) -> str:
        """Retorna uma transcrição de uma única fala."""


class SpeechSynthesizer(Protocol):
    def speak(self, text: str, *, locale: str) -> None:
        """Reproduz uma resposta em voz."""


@dataclass(slots=True)
class NullSpeechCapture:
    reason: str = "Nenhum adaptador de captura de áudio foi configurado."

    def listen(self, *, locale: str) -> str:
        del locale
        raise RuntimeError(self.reason)


@dataclass(slots=True)
class NullSpeechSynthesizer:
    def speak(self, text: str, *, locale: str) -> None:
        del text, locale


@dataclass(frozen=True, slots=True)
class VoiceTurn:
    activated: bool
    command: str | None
    response: str | None
    spoken: bool
    reason: str = ""


class VoiceSession:
    """Conecta transcrição, palavra de ativação, runtime e síntese opcional."""

    def __init__(
        self,
        runtime: ZeusRuntime,
        *,
        config: VoiceConfig | None = None,
        capture: SpeechCapture | None = None,
        synthesizer: SpeechSynthesizer | None = None,
    ) -> None:
        self.runtime = runtime
        self.config = config or VoiceConfig.from_env()
        self.capture = capture or NullSpeechCapture()
        self.synthesizer = synthesizer or NullSpeechSynthesizer()

    def process_transcript(self, transcript: str, *, mode: str = "assistant") -> VoiceTurn:
        if not self.config.enabled:
            return VoiceTurn(False, None, None, False, "Voz desativada.")

        command = extract_wake_command(transcript, self.config)
        if command is None:
            return VoiceTurn(False, None, None, False, "Palavra de ativação não detectada.")
        response = "Estou ouvindo." if not command else self.runtime.handle(command, mode=mode)

        try:
            self.synthesizer.speak(response, locale=self.config.locale)
        except Exception as exc:
            return VoiceTurn(
                True,
                command,
                response,
                False,
                f"Resposta processada, mas a síntese falhou: {type(exc).__name__}.",
            )
        return VoiceTurn(True, command, response, True)

    def listen_once(self, *, mode: str = "assistant") -> VoiceTurn:
        if not self.config.enabled:
            return VoiceTurn(False, None, None, False, "Voz desativada.")
        try:
            transcript = self.capture.listen(locale=self.config.locale)
        except Exception as exc:
            return VoiceTurn(False, None, None, False, f"Falha de captura: {type(exc).__name__}.")
        return self.process_transcript(transcript, mode=mode)


__all__ = [
    "NullSpeechCapture",
    "NullSpeechSynthesizer",
    "SpeechCapture",
    "SpeechSynthesizer",
    "VoiceSession",
    "VoiceTurn",
]
