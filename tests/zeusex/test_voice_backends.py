"""Testes dos backends opcionais de voz do ZeusExAI."""

from __future__ import annotations

import pytest

from openjarvis.zeusex.voice import VoiceConfig, voice_status
from openjarvis.zeusex.voice_backends import (
    FasterWhisperCapture,
    Pyttsx3Synthesizer,
    VoiceBackendError,
    build_capture_backend,
    build_synthesizer_backend,
)
from openjarvis.zeusex.voice_runtime import NullSpeechCapture, NullSpeechSynthesizer


def test_voice_config_reads_backend_environment(monkeypatch) -> None:
    monkeypatch.setenv("ZEUSEX_VOICE_ENABLED", "true")
    monkeypatch.setenv("ZEUSEX_VOICE_CAPTURE", "faster-whisper")
    monkeypatch.setenv("ZEUSEX_VOICE_SYNTHESIZER", "pyttsx3")
    monkeypatch.setenv("ZEUSEX_VOICE_MODEL", "tiny")
    monkeypatch.setenv("ZEUSEX_VOICE_LISTEN_SECONDS", "7")

    config = VoiceConfig.from_env()

    assert config.enabled is True
    assert config.capture_backend == "faster-whisper"
    assert config.synthesizer_backend == "pyttsx3"
    assert config.model == "tiny"
    assert config.listen_seconds == 7.0
    assert "Captura: faster-whisper" in voice_status(config)


def test_voice_listen_duration_is_bounded(monkeypatch) -> None:
    monkeypatch.setenv("ZEUSEX_VOICE_LISTEN_SECONDS", "500")

    assert VoiceConfig.from_env().listen_seconds == 30.0


def test_backend_factories_return_null_adapters() -> None:
    assert isinstance(build_capture_backend("none"), NullSpeechCapture)
    assert isinstance(build_synthesizer_backend("none"), NullSpeechSynthesizer)


def test_backend_factories_return_real_adapter_objects_without_importing_dependencies() -> None:
    capture = build_capture_backend("faster-whisper", model_name="tiny")
    synthesizer = build_synthesizer_backend("pyttsx3")

    assert isinstance(capture, FasterWhisperCapture)
    assert isinstance(synthesizer, Pyttsx3Synthesizer)
    assert capture.model_name == "tiny"


def test_unknown_voice_backends_are_rejected() -> None:
    with pytest.raises(VoiceBackendError):
        build_capture_backend("shell-command")
    with pytest.raises(VoiceBackendError):
        build_synthesizer_backend("remote-unknown")
