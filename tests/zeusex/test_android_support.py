"""Testes do suporte Android reproduzível."""

from pathlib import Path
import json
import sqlite3

import pytest

from openjarvis.zeusex.android_support import (
    AndroidPackageManifest,
    backup_android_databases,
    build_android_update_plan,
    diagnose_android,
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


def test_backup_rejects_same_source_and_destination(tmp_path) -> None:
    with pytest.raises(ValueError, match="diferente"):
        backup_android_databases(tmp_path, tmp_path)


def test_update_plan_requires_safe_git_reference() -> None:
    plan = build_android_update_plan("develop-zeusex")

    assert plan.ref == "develop-zeusex"
    assert "backup" in plan.render().lower()
    assert "apagar" in plan.render().lower()
    with pytest.raises(ValueError, match="Git inválida"):
        build_android_update_plan("../perigoso")
    with pytest.raises(ValueError, match="Git inválida"):
        build_android_update_plan("--force")
