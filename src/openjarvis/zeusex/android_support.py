"""Diagnóstico, manifesto e preservação de dados no Android/Termux."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
import json
import os
import re
import sqlite3
import sys

DATABASE_FILENAMES = (
    "zeusex.db",
    "marketplace-queue.db",
    "marketplace-reports.db",
    "campaign-templates.db",
    "schedules.db",
)


@dataclass(frozen=True, slots=True)
class AndroidDiagnostic:
    termux_detected: bool
    python_version: str
    python_supported: bool
    data_dir: str
    data_dir_exists: bool
    data_dir_writable: bool
    databases: tuple[str, ...]
    server_host: str
    network_scope: str


def diagnose_android(
    data_dir: Path | str,
    *,
    environment: Mapping[str, str] | None = None,
) -> AndroidDiagnostic:
    env = dict(os.environ if environment is None else environment)
    prefix = env.get("PREFIX", "")
    termux_detected = bool(env.get("TERMUX_VERSION")) or "com.termux" in prefix
    path = Path(data_dir).expanduser()
    exists = path.exists()
    writable = os.access(path, os.W_OK) if exists else os.access(path.parent, os.W_OK)
    databases = tuple(
        filename
        for filename in DATABASE_FILENAMES
        if (path / filename).is_file()
    )
    version_info = sys.version_info
    supported = (3, 10) <= version_info[:2] <= (3, 13)
    return AndroidDiagnostic(
        termux_detected=termux_detected,
        python_version=f"{version_info.major}.{version_info.minor}.{version_info.micro}",
        python_supported=supported,
        data_dir=str(path),
        data_dir_exists=exists,
        data_dir_writable=writable,
        databases=databases,
        server_host="127.0.0.1",
        network_scope="loopback-only",
    )


@dataclass(frozen=True, slots=True)
class AndroidPackageManifest:
    name: str = "ZeusEXai Android/Termux"
    schema_version: int = 1
    python_minimum: str = "3.10"
    python_maximum_tested: str = "3.13"
    entrypoint: str = "jarvis zeusex"
    server_command: str = "jarvis zeusex mobile-serve"
    bind_host: str = "127.0.0.1"
    data_environment: str = "ZEUSEX_DATA_DIR"
    token_environment: str = "ZEUSEX_MOBILE_API_TOKEN"
    databases: tuple[str, ...] = DATABASE_FILENAMES

    def to_json(self) -> str:
        return json.dumps(
            asdict(self),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


@dataclass(frozen=True, slots=True)
class BackupResult:
    destination: Path
    files: tuple[Path, ...]


def backup_android_databases(
    data_dir: Path | str,
    backup_root: Path | str,
) -> BackupResult:
    """Cria snapshots consistentes apenas dos bancos conhecidos."""

    source_root = Path(data_dir).expanduser().resolve()
    destination_root = Path(backup_root).expanduser().resolve()
    if source_root == destination_root:
        raise ValueError("A pasta de backup precisa ser diferente da pasta de dados.")
    if not source_root.is_dir():
        raise ValueError("A pasta de dados não existe.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = destination_root / f"zeusex-backup-{stamp}"
    destination.mkdir(parents=True, exist_ok=False)
    saved: list[Path] = []
    for filename in DATABASE_FILENAMES:
        source = source_root / filename
        if not source.is_file():
            continue
        target = destination / filename
        try:
            with sqlite3.connect(source) as source_db:
                with sqlite3.connect(target) as target_db:
                    source_db.backup(target_db)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Falha ao salvar o banco {filename}.") from exc
        saved.append(target)
    return BackupResult(destination=destination, files=tuple(saved))


@dataclass(frozen=True, slots=True)
class AndroidUpdatePlan:
    ref: str
    steps: tuple[str, ...]

    def render(self) -> str:
        return "\n".join(
            f"{index}. {step}"
            for index, step in enumerate(self.steps, start=1)
        )


def build_android_update_plan(ref: str = "develop-zeusex") -> AndroidUpdatePlan:
    clean_ref = ref.strip()
    if (
        not clean_ref
        or clean_ref.startswith("-")
        or ".." in clean_ref
        or not re.fullmatch(r"[A-Za-z0-9._/-]+", clean_ref)
    ):
        raise ValueError("Referência Git inválida.")
    return AndroidUpdatePlan(
        ref=clean_ref,
        steps=(
            "Encerrar o servidor local com Ctrl+C.",
            "Executar o backup SQLite com 'jarvis zeusex android backup --confirm'.",
            "Confirmar que o backup contém os bancos esperados.",
            f"Buscar e revisar a referência Git '{clean_ref}' sem apagar a pasta de dados.",
            "Atualizar o código somente após a revisão.",
            "Reativar o ambiente virtual e executar 'python -m pip install -e .'.",
            "Executar 'jarvis zeusex android diagnose'.",
            "Iniciar novamente com 'jarvis zeusex mobile-serve'.",
        ),
    )


__all__ = [
    "AndroidDiagnostic",
    "AndroidPackageManifest",
    "AndroidUpdatePlan",
    "BackupResult",
    "DATABASE_FILENAMES",
    "backup_android_databases",
    "build_android_update_plan",
    "diagnose_android",
]
