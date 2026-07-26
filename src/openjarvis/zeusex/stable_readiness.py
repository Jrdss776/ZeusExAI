"""Critérios explícitos para promover uma Beta do ZeusExAI à versão estável."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class StableReadinessCheck:
    component: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StableReadinessReport:
    ready: bool
    checks: tuple[StableReadinessCheck, ...]
    blockers: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "checks": [check.to_dict() for check in self.checks],
            "blockers": self.blockers,
        }


def assess_stable_readiness(
    *,
    beta_days: int,
    acceptance_runs: int,
    validated_platforms: Iterable[str],
    open_critical_bugs: int,
) -> StableReadinessReport:
    """Avalia evidências informadas; não consulta rede nem cria telemetria."""

    if beta_days < 0 or acceptance_runs < 0 or open_critical_bugs < 0:
        raise ValueError("Contagens de estabilização não podem ser negativas.")

    platforms = {value.strip().lower() for value in validated_platforms if value.strip()}
    checks = (
        StableReadinessCheck(
            "periodo_beta",
            "ok" if beta_days >= 7 else "blocker",
            f"Beta observada por {beta_days} dia(s); mínimo exigido: 7.",
        ),
        StableReadinessCheck(
            "aceitacao",
            "ok" if acceptance_runs >= 2 else "blocker",
            f"Aceitação completa aprovada {acceptance_runs} vez(es); mínimo exigido: 2.",
        ),
        StableReadinessCheck(
            "windows",
            "ok" if "windows" in platforms else "blocker",
            "Instalação real validada no Windows."
            if "windows" in platforms
            else "Falta validar uma instalação real no Windows.",
        ),
        StableReadinessCheck(
            "android",
            "ok" if "android" in platforms else "blocker",
            "Instalação real validada no Android/Termux."
            if "android" in platforms
            else "Falta validar uma instalação real no Android/Termux.",
        ),
        StableReadinessCheck(
            "bugs_criticos",
            "ok" if open_critical_bugs == 0 else "blocker",
            "Nenhum bug crítico permanece aberto."
            if open_critical_bugs == 0
            else f"Há {open_critical_bugs} bug(s) crítico(s) aberto(s).",
        ),
    )
    blockers = sum(check.status == "blocker" for check in checks)
    return StableReadinessReport(blockers == 0, checks, blockers)


__all__ = ["StableReadinessCheck", "StableReadinessReport", "assess_stable_readiness"]
