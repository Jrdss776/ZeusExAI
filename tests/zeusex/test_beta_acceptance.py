"""Critério completo de aceitação da Beta."""

from click.testing import CliRunner

from openjarvis.cli.zeusex_cmd import zeusex
from openjarvis.zeusex.beta_acceptance import BETA_VERSION, run_beta_acceptance


def _ready_environment(tmp_path):
    return {
        "ZEUSEX_DATA_DIR": str(tmp_path),
        "ZEUSEX_AI_PROVIDER": "ollama",
        "ZEUSEX_AI_MODEL": "qwen2.5:3b",
    }


def test_beta_acceptance_approves_ready_runtime(tmp_path) -> None:
    result = run_beta_acceptance(
        environment=_ready_environment(tmp_path),
        python_version=(3, 12),
    )
    assert result.version == BETA_VERSION
    assert result.approved is True
    assert result.readiness.ready is True
    assert result.smoke.ok is True


def test_beta_acceptance_blocks_incomplete_configuration(tmp_path) -> None:
    result = run_beta_acceptance(
        environment={"ZEUSEX_DATA_DIR": str(tmp_path)},
        python_version=(3, 12),
    )
    assert result.approved is False
    assert result.readiness.blockers == 1
    assert result.smoke.ok is True


def test_beta_version_cli_identifies_candidate() -> None:
    result = CliRunner().invoke(zeusex, ["beta-version"])
    assert result.exit_code == 0
    assert f"ZeusExAI {BETA_VERSION}" in result.output


def test_beta_acceptance_cli_blocks_without_provider(tmp_path) -> None:
    result = CliRunner().invoke(
        zeusex,
        ["beta-acceptance"],
        env={"ZEUSEX_DATA_DIR": str(tmp_path), "ZEUSEX_AI_PROVIDER": "disabled"},
    )
    assert result.exit_code == 1
    assert "Aceitação Beta: BLOQUEADA" in result.output
