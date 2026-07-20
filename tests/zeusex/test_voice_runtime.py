"""Testes da sessão segura e adaptadores opcionais de voz."""

from __future__ import annotations

from dataclasses import dataclass, field

from openjarvis.zeusex.runtime import RuntimeConfig, ZeusRuntime
from openjarvis.zeusex.voice import VoiceConfig
from openjarvis.zeusex.voice_runtime import VoiceSession


@dataclass
class FakeSynthesizer:
    spoken: list[tuple[str, str]] = field(default_factory=list)

    def speak(self, text: str, *, locale: str) -> None:
        self.spoken.append((text, locale))


@dataclass
class FakeCapture:
    transcript: str

    def listen(self, *, locale: str) -> str:
        assert locale == "pt-BR"
        return self.transcript


def _runtime(tmp_path) -> ZeusRuntime:
    return ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path), skills=None)


def test_voice_session_ignores_transcript_without_wake_word(tmp_path) -> None:
    speaker = FakeSynthesizer()
    session = VoiceSession(
        _runtime(tmp_path),
        config=VoiceConfig(enabled=True),
        synthesizer=speaker,
    )

    turn = session.process_transcript("abrir calculadora")

    assert turn.activated is False
    assert speaker.spoken == []


def test_voice_session_routes_command_without_bypassing_confirmation(tmp_path) -> None:
    session = VoiceSession(_runtime(tmp_path), config=VoiceConfig(enabled=True))

    turn = session.process_transcript("Zeus skill open-app calculator")

    assert turn.activated is True
    assert turn.command == "skill open-app calculator"
    assert "Confirmação necessária" in (turn.response or "")


def test_voice_session_preserves_explicit_confirmation_command(tmp_path) -> None:
    session = VoiceSession(_runtime(tmp_path), config=VoiceConfig(enabled=True))

    turn = session.process_transcript("Zeus confirmar-skill open-app unknown-app")

    assert turn.activated is True
    assert "não permitido" in (turn.response or "").lower()


def test_listen_once_uses_capture_and_synthesizer(tmp_path) -> None:
    speaker = FakeSynthesizer()
    session = VoiceSession(
        _runtime(tmp_path),
        config=VoiceConfig(enabled=True),
        capture=FakeCapture("Zeus status"),
        synthesizer=speaker,
    )

    turn = session.listen_once()

    assert turn.activated is True
    assert "ZeusExAI online" in (turn.response or "")
    assert speaker.spoken and speaker.spoken[0][1] == "pt-BR"


def test_voice_session_stays_inactive_when_disabled(tmp_path) -> None:
    session = VoiceSession(_runtime(tmp_path), config=VoiceConfig(enabled=False))

    turn = session.process_transcript("Zeus status")

    assert turn.activated is False
    assert turn.reason == "Voz desativada."
