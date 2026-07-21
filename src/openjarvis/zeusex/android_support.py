"""Diagnóstico, manifesto e preservação de dados no Android/Termux."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping
import hashlib
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
BACKUP_MANIFEST = "backup-manifest.json"
DATABASE_SCHEMA_VERSION = 1


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


@dataclass(frozen=True, slots=True)
class BackupVerification:
    source: Path
    valid: bool
    databases: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RestoreResult:
    destination: Path
    files: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class AndroidHealth:
    healthy: bool
    databases: tuple[str, ...]
    schema_versions: tuple[tuple[str, int], ...]
    errors: tuple[str, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sqlite_integrity(path: Path) -> str | None:
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()
    except sqlite3.Error:
        return "banco SQLite inválido"
    return None if result and result[0] == "ok" else "falha na integridade SQLite"


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
    manifest = {
        "schema_version": 1,
        "databases": {
            path.name: {"sha256": _sha256(path), "size": path.stat().st_size}
            for path in saved
        },
    }
    (destination / BACKUP_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return BackupResult(destination=destination, files=tuple(saved))


def verify_android_backup(backup_dir: Path | str) -> BackupVerification:
    source = Path(backup_dir).expanduser().resolve()
    errors: list[str] = []
    manifest_path = source / BACKUP_MANIFEST
    if not source.is_dir():
        return BackupVerification(source, False, (), ("A pasta de backup não existe.",))
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest["databases"]
    except (OSError, ValueError, KeyError, TypeError):
        return BackupVerification(source, False, (), ("Manifesto de backup inválido.",))
    if not isinstance(entries, dict):
        return BackupVerification(source, False, (), ("Manifesto de backup inválido.",))

    databases: list[str] = []
    for filename, metadata in entries.items():
        if filename not in DATABASE_FILENAMES or not isinstance(metadata, dict):
            errors.append("O manifesto contém um banco não autorizado.")
            continue
        path = source / filename
        if not path.is_file() or _sha256(path) != metadata.get("sha256"):
            errors.append(f"Falha na assinatura do banco {filename}.")
            continue
        integrity_error = _sqlite_integrity(path)
        if integrity_error:
            errors.append(f"{filename}: {integrity_error}.")
            continue
        databases.append(filename)
    return BackupVerification(source, not errors, tuple(databases), tuple(errors))


def restore_android_backup(
    backup_dir: Path | str,
    data_dir: Path | str,
    *,
    replace: bool = False,
) -> RestoreResult:
    verification = verify_android_backup(backup_dir)
    if not verification.valid:
        raise ValueError("O backup não passou na verificação.")
    destination = Path(data_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    restored: list[Path] = []
    for filename in verification.databases:
        target = destination / filename
        if target.exists() and not replace:
            raise ValueError(f"O banco {filename} já existe; use substituição explícita.")
        try:
            with sqlite3.connect(verification.source / filename) as source_db:
                with sqlite3.connect(target) as target_db:
                    source_db.backup(target_db)
        except (OSError, sqlite3.Error) as exc:
            raise RuntimeError(f"Falha ao restaurar o banco {filename}.") from exc
        restored.append(target)
    return RestoreResult(destination, tuple(restored))


def migrate_android_databases(data_dir: Path | str) -> tuple[tuple[str, int], ...]:
    """Registra a versão do esquema sem modificar tabelas de domínio."""

    root = Path(data_dir).expanduser().resolve()
    versions: list[tuple[str, int]] = []
    for filename in DATABASE_FILENAMES:
        path = root / filename
        if not path.is_file():
            continue
        with sqlite3.connect(path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS zeusex_schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT OR IGNORE INTO zeusex_schema_migrations(version, applied_at) "
                "VALUES (?, ?)",
                (DATABASE_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat()),
            )
        versions.append((filename, DATABASE_SCHEMA_VERSION))
    return tuple(versions)


def check_android_health(data_dir: Path | str) -> AndroidHealth:
    root = Path(data_dir).expanduser().resolve()
    errors: list[str] = []
    databases: list[str] = []
    versions: list[tuple[str, int]] = []
    for filename in DATABASE_FILENAMES:
        path = root / filename
        if not path.is_file():
            continue
        databases.append(filename)
        integrity_error = _sqlite_integrity(path)
        if integrity_error:
            errors.append(f"{filename}: {integrity_error}.")
            continue
        try:
            with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
                row = connection.execute(
                    "SELECT max(version) FROM zeusex_schema_migrations"
                ).fetchone()
            versions.append((filename, int(row[0] or 0)))
        except sqlite3.Error:
            versions.append((filename, 0))
    return AndroidHealth(not errors, tuple(databases), tuple(versions), tuple(errors))


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
    "AndroidHealth",
    "BackupVerification",
    "BackupResult",
    "RestoreResult",
    "DATABASE_FILENAMES",
    "backup_android_databases",
    "build_android_update_plan",
    "check_android_health",
    "diagnose_android",
    "migrate_android_databases",
    "restore_android_backup",
    "verify_android_backup",
]
