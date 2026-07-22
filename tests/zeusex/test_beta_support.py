"""Relatório sanitizado para suporte da Beta."""

from datetime import datetime, timezone
import json

import pytest
from click.testing import CliRunner

from openjarvis.cli.zeusex_cmd import zeusex
from openjarvis.zeusex.beta_support import (
    build_beta_support_snapshot,
    write_beta_support_report,
)


def test_beta_support_snapshot_never_serializes_environment(tmp_path) -> None:
    snapshot = build_beta_support_snapshot(
        environment={
            "ZEUSEX_DATA_DIR": str(tmp_path),
            "ZEUSEX_AI_PROVIDER": "openai",
            "ZEUSEX_AI_MODEL": "modelo",
            "ZEUSEX_AI_API_KEY": "segredo-absoluto",
            "ZEUSEX_MOBILE_API_TOKEN": "token-super-secreto",
        },
        python_version=(3, 12),
        operating_system="Windows",
        system_release="11",
        generated_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
    )
    rendered = snapshot.to_json()
    assert "segredo-absoluto" not in rendered
    assert "token-super-secreto" not in rendered
    assert json.loads(rendered)["readiness"]["ready"] is True


def test_beta_support_report_requires_json_and_explicit_replace(tmp_path) -> None:
    snapshot = build_beta_support_snapshot(
        environment={"ZEUSEX_DATA_DIR": str(tmp_path)},
        python_version=(3, 12),
    )
    with pytest.raises(ValueError, match=".json"):
        write_beta_support_report(snapshot, tmp_path / "report.txt")

    target = write_beta_support_report(snapshot, tmp_path / "report.json")
    with pytest.raises(ValueError, match="substituição"):
        write_beta_support_report(snapshot, target)
    assert write_beta_support_report(snapshot, target, replace=True) == target


def test_beta_report_cli_writes_sanitized_file(tmp_path) -> None:
    target = tmp_path / "support.json"
    result = CliRunner().invoke(
        zeusex,
        ["beta-report", "--output", str(target)],
        env={"ZEUSEX_DATA_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert target.is_file()
    assert "Relatório Beta salvo" in result.output
