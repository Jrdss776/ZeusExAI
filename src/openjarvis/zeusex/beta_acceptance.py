"""Critério único de aceitação do candidato Beta ZeusExAI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.beta_readiness import (
    BetaReadinessReport,
    assess_beta_readiness,
)
from openjarvis.zeusex.beta_smoke import BetaSmokeResult, run_beta_smoke_test

BETA_VERSION = "0.9.0-beta.1"


@dataclass(frozen=True, slots=True)
class BetaAcceptanceResult:
    version: str
    approved: bool
    readiness: BetaReadinessReport
    smoke: BetaSmokeResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "approved": self.approved,
            "readiness": self.readiness.to_dict(),
            "smoke": self.smoke.to_dict(),
        }


def run_beta_acceptance(
    *,
    environment: Mapping[str, str] | None = None,
    python_version: tuple[int, int] | None = None,
) -> BetaAcceptanceResult:
    """Aprova somente quando configuração e runtime isolado passam."""

    readiness = assess_beta_readiness(
        environment=environment,
        python_version=python_version,
    )
    smoke = run_beta_smoke_test()
    return BetaAcceptanceResult(
        version=BETA_VERSION,
        approved=readiness.ready and smoke.ok,
        readiness=readiness,
        smoke=smoke,
    )


__all__ = ["BETA_VERSION", "BetaAcceptanceResult", "run_beta_acceptance"]
