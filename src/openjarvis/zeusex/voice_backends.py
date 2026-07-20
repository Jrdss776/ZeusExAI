"""Backends reais e opcionais de voz para o ZeusExAI.

As dependências são importadas de forma tardia. Instalar o núcleo do projeto não
ativa microfone nem exige bibliotecas de áudio.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from tempfile import NamedTemporaryFile
from typing import Any
import wave

from openjarvis.zeusex.voice_runtime import (
    NullSpeechCapture,
    NullSpeechSynthesizer,
    SpeechCapture,
    SpeechSynthesizer,
)


class VoiceBackendError(RuntimeError):
    """Erro controlado de configuração ou disponibilidade de backend."""


@dataclass(slots=True)
class FasterWhisperCapture:
    """Captura uma fala curta e transcreve localmente com Faster Whisper."""

    model_name: str = "small"
    duration_seconds: float = 5.0
    sample_rate: int = 16000
    device: str = "auto"
    compute_type: str = "int8"
    _model: Any = None

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                module = import_module("faster_whisper")
            except ImportError as exc:
                raise VoiceBackendError(
                    "Backend faster-whisper não instalado. Instale o extra 'zeusex-voice'."
                ) from exc
            self._model = module.WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def listen(self, *, locale: str) -> str:
        try:
            sounddevice = import_module("sounddevice")
        except ImportError as exc:
            raise VoiceBackendError(
                "Captura sounddevice não instalada. Instale o extra 'zeusex-voice'."
            ) from exc

        frames = max(1, int(self.duration_seconds * self.sample_rate))
        try:
            audio = sounddevice.rec(
                frames,
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
            )
            sounddevice.wait()
        except Exception as exc:
            raise VoiceBackendError("Não foi possível capturar áudio do microfone.") from exc

        language = locale.split("-", 1)[0].lower() or "pt"
        with NamedTemporaryFile(suffix=".wav") as temp:
            with wave.open(temp.name, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio.tobytes())
            segments, _ = self._load_model().transcribe(temp.name, language=language)
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript


@dataclass(slots=True)
class Pyttsx3Synthesizer:
    """Síntese local via pyttsx3, sem serviço de nuvem."""

    rate: int = 180
    volume: float = 1.0
    _engine: Any = None

    def _load_engine(self) -> Any:
        if self._engine is None:
            try:
                module = import_module("pyttsx3")
            except ImportError as exc:
                raise VoiceBackendError(
                    "Backend pyttsx3 não instalado. Instale o extra 'zeusex-voice'."
                ) from exc
            self._engine = module.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", max(0.0, min(1.0, self.volume)))
        return self._engine

    def speak(self, text: str, *, locale: str) -> None:
        del locale
        clean = text.strip()
        if not clean:
            return
        engine = self._load_engine()
        engine.say(clean)
        engine.runAndWait()


def build_capture_backend(name: str, **options: Any) -> SpeechCapture:
    normalized = name.strip().lower()
    if normalized in {"", "none", "null", "disabled"}:
        return NullSpeechCapture()
    if normalized in {"faster-whisper", "whisper"}:
        return FasterWhisperCapture(**options)
    raise VoiceBackendError(f"Backend de captura desconhecido: {name}.")


def build_synthesizer_backend(name: str, **options: Any) -> SpeechSynthesizer:
    normalized = name.strip().lower()
    if normalized in {"", "none", "null", "disabled"}:
        return NullSpeechSynthesizer()
    if normalized in {"pyttsx3", "local"}:
        return Pyttsx3Synthesizer(**options)
    raise VoiceBackendError(f"Backend de síntese desconhecido: {name}.")


__all__ = [
    "FasterWhisperCapture",
    "Pyttsx3Synthesizer",
    "VoiceBackendError",
    "build_capture_backend",
    "build_synthesizer_backend",
]
