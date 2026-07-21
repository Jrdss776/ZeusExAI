"""Diagnóstico offline de prontidão para a primeira Beta do ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping
import os
import sys


@dataclass(frozen=True, slots=True)
class BetaReadinessCheck:
    component: str
    status: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class BetaReadinessReport:
    ready: bool
    checks: tuple[BetaReadinessCheck, ...]
    blockers: int
    warnings: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "checks": [check.to_dict() for check in self.checks],
        }


def _enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "sim"}


def assess_beta_readiness(
    *,
    environment: Mapping[str, str] | None = None,
    python_version: tuple[int, int] | None = None,
) -> BetaReadinessReport:
    """Avalia configuração local sem rede, microfone ou gravação de dados."""

    env = dict(os.environ if environment is None else environment)
    version = python_version or (sys.version_info.major, sys.version_info.minor)
    checks: list[BetaReadinessCheck] = []

    supported = (3, 10) <= version <= (3, 13)
    checks.append(
        BetaReadinessCheck(
            "python",
            "ok" if supported else "blocker",
            f"Python {version[0]}.{version[1]} "
            + ("compatível." if supported else "fora da faixa 3.10–3.13."),
        )
    )

    data_dir = Path(env.get("ZEUSEX_DATA_DIR", ".zeusex")).expanduser()
    writable_target = data_dir if data_dir.exists() else data_dir.parent
    writable = writable_target.exists() and os.access(writable_target, os.W_OK)
    checks.append(
        BetaReadinessCheck(
            "dados",
            "ok" if writable else "blocker",
            "Pasta de dados disponível para o runtime."
            if writable
            else "A pasta de dados não pode ser criada ou atualizada.",
        )
    )

    provider = env.get("ZEUSEX_AI_PROVIDER", "disabled").strip().lower()
    model = env.get("ZEUSEX_AI_MODEL", "").strip()
    key_ready = bool(env.get("ZEUSEX_AI_API_KEY", "").strip())
    provider_ready = provider not in {"", "disabled", "none", "off"} and bool(model)
    if provider in {"openai", "openai-compatible", "compatible"}:
        provider_ready = provider_ready and key_ready
    checks.append(
        BetaReadinessCheck(
            "ia",
            "ok" if provider_ready else "blocker",
            "Motor de IA configurado; credenciais não foram exibidas."
            if provider_ready
            else "Configure provedor, modelo e credencial quando aplicável.",
        )
    )

    token = env.get("ZEUSEX_MOBILE_API_TOKEN", "")
    token_ready = len(token) >= 16
    checks.append(
        BetaReadinessCheck(
            "painel_movel",
            "ok" if token_ready else "warning",
            "Token local do painel configurado."
            if token_ready
            else "Painel móvel opcional sem token local de 16 caracteres.",
        )
    )

    voice_enabled = _enabled(env.get("ZEUSEX_VOICE_ENABLED", "false"))
    capture = env.get("ZEUSEX_VOICE_CAPTURE", "none").strip().lower()
    synthesizer = env.get("ZEUSEX_VOICE_SYNTHESIZER", "none").strip().lower()
    voice_ready = voice_enabled and capture != "none" and synthesizer != "none"
    checks.append(
        BetaReadinessCheck(
            "voz",
            "ok" if voice_ready else "warning",
            "Voz habilitada com captura e síntese configuradas."
            if voice_ready
            else "Voz é opcional na Beta e ainda não está totalmente configurada.",
        )
    )

    blockers = sum(check.status == "blocker" for check in checks)
    warnings = sum(check.status == "warning" for check in checks)
    return BetaReadinessReport(blockers == 0, tuple(checks), blockers, warnings)


__all__ = ["BetaReadinessCheck", "BetaReadinessReport", "assess_beta_readiness"]
