"""Backends reais e opcionais de voz para o ZeusExAI.

As dependências são importadas de forma tardia. Instalar o núcleo do projeto não
ativa microfone nem exige bibliotecas de áudio.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from tempfile import NamedTemporaryFile
from typing import Any
import unicodedata
import wave

from openjarvis.zeusex.voice_runtime import (
    NullSpeechCapture,
    NullSpeechSynthesizer,
    SpeechCapture,
    SpeechSynthesizer,
)


class VoiceBackendError(RuntimeError):
    """Erro controlado de configuração ou disponibilidade de backend."""


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def list_input_devices() -> list[dict[str, object]]:
    """Lista somente dispositivos com canais de entrada, sem iniciar captura."""

    try:
        sounddevice = import_module("sounddevice")
    except ImportError as exc:
        raise VoiceBackendError(
            "Captura sounddevice não instalada. Instale o extra 'zeusex-voice'."
        ) from exc
    try:
        devices = sounddevice.query_devices()
    except Exception as exc:
        raise VoiceBackendError("Não foi possível consultar dispositivos de áudio.") from exc

    result: list[dict[str, object]] = []
    for index, device in enumerate(devices):
        channels = int(device.get("max_input_channels", 0))
        if channels > 0:
            result.append({
                "id": index,
                "name": str(device.get("name", "dispositivo sem nome")),
                "channels": channels,
                "sample_rate": int(float(device.get("default_samplerate", 0) or 0)),
            })
    return result


def validate_input_device(device_id: int | None) -> int | None:
    if device_id is None:
        return None
    available = {int(item["id"]) for item in list_input_devices()}
    if device_id not in available:
        raise VoiceBackendError("Dispositivo de entrada inválido ou sem canais de captura.")
    return device_id


@dataclass(slots=True)
class FasterWhisperCapture:
    """Captura uma fala curta e transcreve localmente com Faster Whisper."""

    model_name: str = "small"
    duration_seconds: float = 5.0
    sample_rate: int = 16000
    device: str = "auto"
    compute_type: str = "int8"
    input_device: int | None = None
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

        selected_device = validate_input_device(self.input_device)
        frames = max(1, int(self.duration_seconds * self.sample_rate))
        try:
            audio = sounddevice.rec(
                frames,
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                device=selected_device,
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
    """Síntese local via pyttsx3, com preferência por voz pt-BR."""

    rate: int = 180
    volume: float = 1.0
    preferred_voice: str = "pt-BR"
    _engine: Any = None

    def _select_voice(self, engine: Any, locale: str) -> None:
        targets = [_normalize(self.preferred_voice), _normalize(locale), "portuguese", "brazil"]
        try:
            voices = engine.getProperty("voices") or []
        except Exception:
            return
        for voice in voices:
            languages = " ".join(str(item) for item in getattr(voice, "languages", []) or [])
            haystack = _normalize(
                " ".join([
                    str(getattr(voice, "id", "")),
                    str(getattr(voice, "name", "")),
                    languages,
                ])
            )
            if any(target and target in haystack for target in targets):
                engine.setProperty("voice", voice.id)
                return

    def _load_engine(self, locale: str) -> Any:
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
            self._select_voice(self._engine, locale)
        return self._engine

    def speak(self, text: str, *, locale: str) -> None:
        clean = text.strip()
        if not clean:
            return
        engine = self._load_engine(locale)
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
    "list_input_devices",
    "validate_input_device",
]
