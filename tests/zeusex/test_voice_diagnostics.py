"""Testes de diagnóstico e configuração segura de voz."""

from openjarvis.zeusex.voice import VoiceConfig
from openjarvis.zeusex.voice_backends import Pyttsx3Synthesizer, validate_input_device
from openjarvis.zeusex.voice_diagnostics import diagnose_voice


def test_voice_config_rejects_negative_input_device(monkeypatch) -> None:
    monkeypatch.setenv("ZEUSEX_VOICE_INPUT_DEVICE", "-1")

    config = VoiceConfig.from_env()

    assert config.input_device is None


def test_voice_config_reads_preferred_voice(monkeypatch) -> None:
    monkeypatch.setenv("ZEUSEX_VOICE_PREFERRED_VOICE", "Microsoft Maria")

    config = VoiceConfig.from_env()

    assert config.preferred_voice == "Microsoft Maria"


def test_voice_diagnostics_reports_unknown_backend() -> None:
    config = VoiceConfig(capture_backend="misterioso", synthesizer_backend="none")

    results = diagnose_voice(config)

    capture = next(item for item in results if item.component == "captura")
    assert capture.ok is False
    assert "desconhecido" in capture.message.lower()


def test_default_input_device_needs_no_lookup() -> None:
    assert validate_input_device(None) is None


def test_synthesizer_keeps_preferred_voice() -> None:
    synthesizer = Pyttsx3Synthesizer(preferred_voice="pt-BR")

    assert synthesizer.preferred_voice == "pt-BR"
