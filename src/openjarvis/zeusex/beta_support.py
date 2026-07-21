"""Relatório sanitizado para suporte durante os testes Beta."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import json
import os
import platform
import sys
import tempfile

from openjarvis.zeusex.beta_readiness import (
    BetaReadinessReport,
    assess_beta_readiness,
)


@dataclass(frozen=True, slots=True)
class BetaSupportSnapshot:
    schema_version: int
    generated_at: str
    operating_system: str
    system_release: str
    python_version: str
    readiness: BetaReadinessReport

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["readiness"] = self.readiness.to_dict()
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def build_beta_support_snapshot(
    *,
    environment: Mapping[str, str] | None = None,
    python_version: tuple[int, int] | None = None,
    operating_system: str | None = None,
    system_release: str | None = None,
    generated_at: datetime | None = None,
) -> BetaSupportSnapshot:
    """Coleta somente campos permitidos; o ambiente nunca é serializado."""

    version = python_version or (sys.version_info.major, sys.version_info.minor)
    timestamp = generated_at or datetime.now(timezone.utc)
    return BetaSupportSnapshot(
        schema_version=1,
        generated_at=timestamp.astimezone(timezone.utc).isoformat(),
        operating_system=operating_system or platform.system(),
        system_release=system_release or platform.release(),
        python_version=f"{version[0]}.{version[1]}",
        readiness=assess_beta_readiness(
            environment=environment,
            python_version=version,
        ),
    )


def write_beta_support_report(
    snapshot: BetaSupportSnapshot,
    destination: Path | str,
    *,
    replace: bool = False,
) -> Path:
    """Grava JSON atomicamente e não substitui arquivos sem autorização."""

    target = Path(destination).expanduser().resolve()
    if target.suffix.lower() != ".json":
        raise ValueError("O relatório Beta precisa usar a extensão .json.")
    if not target.parent.is_dir():
        raise ValueError("A pasta de destino não existe.")
    if target.exists() and not replace:
        raise ValueError("O relatório já existe; confirme a substituição.")

    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{target.stem}-",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(snapshot.to_json())
            stream.write("\n")
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return target


__all__ = [
    "BetaSupportSnapshot",
    "build_beta_support_snapshot",
    "write_beta_support_report",
]
