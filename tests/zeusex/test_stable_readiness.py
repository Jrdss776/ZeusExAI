from __future__ import annotations

from click.testing import CliRunner
import pytest

from openjarvis.cli.zeusex_cmd import zeusex
from openjarvis.zeusex.stable_readiness import assess_stable_readiness


def test_stable_readiness_requires_all_promotion_evidence() -> None:
    report = assess_stable_readiness(
        beta_days=7,
        acceptance_runs=2,
        validated_platforms=("windows", "android"),
        open_critical_bugs=0,
    )

    assert report.ready is True
    assert report.blockers == 0
    assert all(check.status == "ok" for check in report.checks)


def test_stable_readiness_reports_each_missing_evidence() -> None:
    report = assess_stable_readiness(
        beta_days=2,
        acceptance_runs=1,
        validated_platforms=("windows",),
        open_critical_bugs=3,
    )

    assert report.ready is False
    assert report.blockers == 4
    assert {check.component for check in report.checks if check.status == "blocker"} == {
        "periodo_beta",
        "aceitacao",
        "android",
        "bugs_criticos",
    }


def test_stable_readiness_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="negativas"):
        assess_stable_readiness(
            beta_days=-1,
            acceptance_runs=0,
            validated_platforms=(),
            open_critical_bugs=0,
        )


def test_stable_readiness_cli_approves_complete_evidence() -> None:
    result = CliRunner().invoke(
        zeusex,
        [
            "stable-readiness",
            "--beta-days", "7",
            "--acceptance-runs", "2",
            "--platform", "windows",
            "--platform", "android",
            "--open-critical-bugs", "0",
        ],
    )

    assert result.exit_code == 0
    assert "Prontidão Estável: APROVADA" in result.output


def test_stable_readiness_cli_blocks_incomplete_evidence() -> None:
    result = CliRunner().invoke(
        zeusex,
        [
            "stable-readiness",
            "--beta-days", "0",
            "--acceptance-runs", "0",
            "--open-critical-bugs", "1",
        ],
    )

    assert result.exit_code == 1
    assert "Prontidão Estável: BLOQUEADA" in result.output
