"""Testes da fundação de voz pt-BR do ZeusExAI."""

from openjarvis.zeusex.voice import VoiceConfig, extract_wake_command, voice_status


def test_extracts_command_after_wake_word() -> None:
    config = VoiceConfig(locale="pt-BR", wake_word="Zeus", enabled=True)

    assert extract_wake_command("Zeus abrir calculadora", config) == "abrir calculadora"


def test_ignores_transcript_without_wake_word() -> None:
    config = VoiceConfig(wake_word="Zeus")

    assert extract_wake_command("abrir calculadora", config) is None


def test_wake_word_is_accent_and_case_tolerant() -> None:
    config = VoiceConfig(wake_word="Zéus")

    assert extract_wake_command("ZEUS lembrar reunião", config) == "lembrar reuniao"


def test_voice_status_does_not_activate_capture() -> None:
    result = voice_status(VoiceConfig(enabled=False))

    assert "desativado" in result
    assert "pt-BR" in result
