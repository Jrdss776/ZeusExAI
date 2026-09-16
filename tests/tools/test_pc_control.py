import json
import os
from pathlib import Path

from openjarvis.tools.pc_control import (
    FolderOrganizerPreviewTool,
    ProcessListTool,
    build_folder_organization_plan,
    execute_folder_organization,
    execute_graceful_process_close,
)


def test_folder_preview_groups_files_and_returns_snapshot(tmp_path: Path) -> None:
    (tmp_path / "foto.jpg").write_bytes(b"jpg")
    (tmp_path / "dados.xlsx").write_bytes(b"xlsx")
    (tmp_path / "script.py").write_text("print('ok')", encoding="utf-8")

    result = FolderOrganizerPreviewTool().execute(path=str(tmp_path))

    assert result.success is True
    plan = build_folder_organization_plan(str(tmp_path))
    assert plan["file_count"] == 3
    assert len(plan["snapshot_hash"]) == 64
    assert {"Imagens", "Planilhas", "Codigo"}.issubset(plan["groups"])


def test_approved_organization_never_overwrites_and_uses_snapshot(tmp_path: Path) -> None:
    source = tmp_path / "relatorio.pdf"
    source.write_text("novo", encoding="utf-8")
    plan = build_folder_organization_plan(str(tmp_path))

    ok, message = execute_folder_organization(str(tmp_path), plan["snapshot_hash"])

    assert ok is True
    assert "1 arquivo" in message
    assert not source.exists()
    assert (tmp_path / "Organizado" / "Documentos" / "relatorio.pdf").read_text(encoding="utf-8") == "novo"


def test_organization_refuses_changed_folder_snapshot(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    plan = build_folder_organization_plan(str(tmp_path))
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")

    ok, message = execute_folder_organization(str(tmp_path), plan["snapshot_hash"])

    assert ok is False
    assert "mudou desde a prévia" in message
    assert (tmp_path / "a.txt").exists()
    assert (tmp_path / "b.txt").exists()


def test_process_list_uses_windows_api_and_returns_current_python() -> None:
    result = ProcessListTool().execute(query="python", limit=50)

    assert result.success is True
    rows = json.loads(result.content)
    assert any(row["pid"] == os.getpid() for row in rows)


def test_process_close_refuses_current_process() -> None:
    ok, message = execute_graceful_process_close(os.getpid(), "python.exe")

    assert ok is False
    assert "protegido" in message
