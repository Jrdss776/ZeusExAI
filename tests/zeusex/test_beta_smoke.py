"""Teste de fumaça isolado da Beta."""

from click.testing import CliRunner

from openjarvis.cli.zeusex_cmd import zeusex
from openjarvis.zeusex.beta_smoke import run_beta_smoke_test


def test_beta_smoke_validates_runtime_and_removes_data(tmp_path) -> None:
    result = run_beta_smoke_test(base_dir=tmp_path)
    assert result.ok is True
    assert result.temporary_data_removed is True
    assert result.external_action_performed is False
    assert {step.name for step in result.steps} == {
        "runtime",
        "sqlite",
        "memoria",
        "comando",
    }
    assert list(tmp_path.iterdir()) == []


def test_beta_smoke_cli_reports_approval() -> None:
    result = CliRunner().invoke(zeusex, ["beta-smoke"])
    assert result.exit_code == 0
    assert "Teste Beta: APROVADO" in result.output
    assert "Dados temporários removidos" in result.output


def test_beta_smoke_result_is_safe_to_serialize(tmp_path) -> None:
    payload = run_beta_smoke_test(base_dir=tmp_path).to_dict()
    assert payload["ok"] is True
    assert payload["external_action_performed"] is False
    assert str(tmp_path) not in str(payload)
