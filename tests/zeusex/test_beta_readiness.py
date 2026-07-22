"""Diagnóstico offline de prontidão para Beta."""

from click.testing import CliRunner

from openjarvis.cli.zeusex_cmd import zeusex
from openjarvis.zeusex.beta_readiness import assess_beta_readiness


def _ready_environment(tmp_path):
    return {
        "ZEUSEX_DATA_DIR": str(tmp_path),
        "ZEUSEX_AI_PROVIDER": "ollama",
        "ZEUSEX_AI_MODEL": "qwen2.5:3b",
        "ZEUSEX_MOBILE_API_TOKEN": "token-local-seguro-123",
        "ZEUSEX_VOICE_ENABLED": "true",
        "ZEUSEX_VOICE_CAPTURE": "faster-whisper",
        "ZEUSEX_VOICE_SYNTHESIZER": "pyttsx3",
    }


def test_beta_readiness_accepts_complete_offline_configuration(tmp_path) -> None:
    report = assess_beta_readiness(
        environment=_ready_environment(tmp_path),
        python_version=(3, 12),
    )
    assert report.ready is True
    assert report.blockers == 0
    assert report.warnings == 0


def test_beta_readiness_blocks_missing_ai_provider(tmp_path) -> None:
    report = assess_beta_readiness(
        environment={"ZEUSEX_DATA_DIR": str(tmp_path)},
        python_version=(3, 12),
    )
    assert report.ready is False
    assert report.blockers == 1
    assert any(check.component == "ia" for check in report.checks)


def test_beta_readiness_never_exposes_api_key(tmp_path) -> None:
    environment = _ready_environment(tmp_path)
    environment["ZEUSEX_AI_PROVIDER"] = "openai"
    environment["ZEUSEX_AI_API_KEY"] = "segredo-que-nao-pode-aparecer"
    report = assess_beta_readiness(environment=environment, python_version=(3, 12))
    assert "segredo-que-nao-pode-aparecer" not in str(report.to_dict())


def test_beta_readiness_cli_returns_failure_for_blockers(tmp_path) -> None:
    result = CliRunner().invoke(
        zeusex,
        ["beta-readiness"],
        env={"ZEUSEX_DATA_DIR": str(tmp_path), "ZEUSEX_AI_PROVIDER": "disabled"},
    )
    assert result.exit_code == 1
    assert "Prontidão Beta: BLOQUEADA" in result.output
