"""Testes do suporte Android reproduzível."""

from pathlib import Path
import json
import sqlite3

import pytest

from openjarvis.zeusex.android_support import (
    AndroidPackageManifest,
    backup_android_databases,
    build_android_update_plan,
    check_android_health,
    diagnose_android,
    migrate_android_databases,
    restore_android_backup,
    verify_android_backup,
)


def _database(path: Path, value: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
        connection.execute("INSERT INTO sample(value) VALUES (?)", (value,))


def test_android_diagnostic_detects_termux_and_known_databases(tmp_path) -> None:
    _database(tmp_path / "zeusex.db", "memória")
    report = diagnose_android(
        tmp_path,
        environment={
            "PREFIX": "/data/data/com.termux/files/usr",
            "TERMUX_VERSION": "1",
        },
    )

    assert report.termux_detected is True
    assert report.network_scope == "loopback-only"
    assert report.server_host == "127.0.0.1"
    assert report.databases == ("zeusex.db",)


def test_package_manifest_is_deterministic_and_contains_no_secret() -> None:
    first = AndroidPackageManifest().to_json()
    second = AndroidPackageManifest().to_json()
    decoded = json.loads(first)

    assert first == second
    assert decoded["bind_host"] == "127.0.0.1"
    assert decoded["token_environment"] == "ZEUSEX_MOBILE_API_TOKEN"
    assert "token-local" not in first


def test_backup_uses_separate_sqlite_snapshots(tmp_path) -> None:
    data = tmp_path / "data"
    backup = tmp_path / "backups"
    data.mkdir()
    _database(data / "zeusex.db", "memória")
    _database(data / "marketplace-reports.db", "relatório")
    (data / "não-copiar.txt").write_text("fora da allowlist", encoding="utf-8")

    result = backup_android_databases(data, backup)

    assert {path.name for path in result.files} == {
        "zeusex.db",
        "marketplace-reports.db",
    }
    assert not (result.destination / "não-copiar.txt").exists()
    with sqlite3.connect(result.destination / "zeusex.db") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "memória"

    verification = verify_android_backup(result.destination)
    assert verification.valid is True
    assert set(verification.databases) == {"zeusex.db", "marketplace-reports.db"}


def test_verification_rejects_tampered_backup(tmp_path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _database(data / "zeusex.db", "original")
    backup = backup_android_databases(data, tmp_path / "backups")
    (backup.destination / "zeusex.db").write_bytes(b"alterado")

    result = verify_android_backup(backup.destination)

    assert result.valid is False
    assert "assinatura" in result.errors[0]


def test_restore_requires_explicit_replace_for_existing_database(tmp_path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    _database(source / "zeusex.db", "backup")
    _database(target / "zeusex.db", "local")
    backup = backup_android_databases(source, tmp_path / "backups")

    with pytest.raises(ValueError, match="substituição explícita"):
        restore_android_backup(backup.destination, target)
    restored = restore_android_backup(backup.destination, target, replace=True)

    assert [path.name for path in restored.files] == ["zeusex.db"]
    with sqlite3.connect(target / "zeusex.db") as connection:
        assert connection.execute("SELECT value FROM sample").fetchone()[0] == "backup"


def test_migrations_are_idempotent_and_health_checks_integrity(tmp_path) -> None:
    _database(tmp_path / "zeusex.db", "memória")

    assert migrate_android_databases(tmp_path) == (("zeusex.db", 1),)
    assert migrate_android_databases(tmp_path) == (("zeusex.db", 1),)
    health = check_android_health(tmp_path)

    assert health.healthy is True
    assert health.schema_versions == (("zeusex.db", 1),)


def test_backup_rejects_same_source_and_destination(tmp_path) -> None:
    with pytest.raises(ValueError, match="diferente"):
        backup_android_databases(tmp_path, tmp_path)


def test_update_plan_requires_safe_git_reference() -> None:
    plan = build_android_update_plan()

    assert plan.ref == "main"
    assert "backup" in plan.render().lower()
    assert "apagar" in plan.render().lower()
    with pytest.raises(ValueError, match="Git inválida"):
        build_android_update_plan("../perigoso")
    with pytest.raises(ValueError, match="Git inválida"):
        build_android_update_plan("--force")
