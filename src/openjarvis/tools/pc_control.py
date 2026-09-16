"""Safe, Windows-friendly inspection tools used by James.

Mutating operations are deliberately not exposed as direct tools.  Folder
organization and graceful process termination are proposed through
``queue_action`` and only run after approval in the desktop UI.
"""

from __future__ import annotations

import hashlib
import ctypes
import json
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from openjarvis.core.registry import ToolRegistry
from openjarvis.core.types import ToolResult
from openjarvis.security.file_policy import is_sensitive_file
from openjarvis.tools._stubs import BaseTool, ToolSpec


_CATEGORIES: dict[str, frozenset[str]] = {
    "Imagens": frozenset({".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".svg", ".webp"}),
    "Documentos": frozenset({".doc", ".docx", ".md", ".pdf", ".ppt", ".pptx", ".rtf", ".txt"}),
    "Planilhas": frozenset({".csv", ".ods", ".xls", ".xlsm", ".xlsx"}),
    "Codigo": frozenset({".c", ".cpp", ".css", ".go", ".html", ".java", ".js", ".json", ".py", ".rs", ".toml", ".ts", ".tsx", ".yaml", ".yml"}),
    "Compactados": frozenset({".7z", ".gz", ".rar", ".tar", ".zip"}),
    "Audio": frozenset({".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}),
    "Video": frozenset({".avi", ".mkv", ".mov", ".mp4", ".webm", ".wmv"}),
}


def _category(path: Path) -> str:
    suffix = path.suffix.casefold()
    for name, extensions in _CATEGORIES.items():
        if suffix in extensions:
            return name
    return "Outros"


def build_folder_organization_plan(directory_value: str) -> dict[str, Any]:
    """Return a bounded, deterministic plan for direct children of a folder."""

    directory = Path(directory_value).expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("O caminho informado não é uma pasta.")
    if directory == Path(directory.anchor) or directory == Path.home().resolve():
        raise ValueError("Por segurança, a raiz do disco e a pasta pessoal inteira não podem ser organizadas.")

    files: list[Path] = []
    skipped: list[str] = []
    for item in sorted(directory.iterdir(), key=lambda value: value.name.casefold()):
        if not item.is_file() or item.name.startswith("."):
            continue
        if is_sensitive_file(item):
            skipped.append(item.name)
            continue
        files.append(item)
        if len(files) > 500:
            raise ValueError("A pasta possui mais de 500 arquivos; divida a organização em partes menores.")

    snapshot_rows: list[str] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in files:
        stat = item.stat()
        snapshot_rows.append(f"{item.name}\0{stat.st_size}\0{stat.st_mtime_ns}")
        group = _category(item)
        groups.setdefault(group, []).append(
            {
                "name": item.name,
                "destination": str(directory / "Organizado" / group / item.name),
            }
        )

    digest = hashlib.sha256("\n".join(snapshot_rows).encode("utf-8")).hexdigest()
    return {
        "directory": str(directory),
        "snapshot_hash": digest,
        "file_count": len(files),
        "groups": groups,
        "skipped_sensitive": skipped,
    }


def execute_folder_organization(path: str, snapshot_hash: str) -> tuple[bool, str]:
    """Apply an approved plan without recursion, deletion, or overwrites."""

    try:
        plan = build_folder_organization_plan(path)
    except (OSError, RuntimeError, ValueError) as exc:
        return False, str(exc)
    if not snapshot_hash or plan["snapshot_hash"] != snapshot_hash:
        return False, "A pasta mudou desde a prévia. Solicite uma nova análise antes de organizar."

    moved = 0
    skipped = 0
    directory = Path(plan["directory"])
    for group, items in plan["groups"].items():
        target_dir = directory / "Organizado" / group
        for item in items:
            source = directory / item["name"]
            target = target_dir / item["name"]
            if not source.is_file() or target.exists():
                skipped += 1
                continue
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            moved += 1
    return True, f"Organização concluída: {moved} arquivo(s) movido(s), {skipped} ignorado(s), nenhum sobrescrito."


def execute_graceful_process_close(pid: int, expected_name: str) -> tuple[bool, str]:
    """Gracefully terminate exactly one approved process; never force-kill it."""

    if pid <= 4 or pid == os.getpid():
        return False, "Processo protegido; encerramento recusado."
    if platform.system() == "Windows":
        rows = _windows_processes(pid=pid)
        if not rows:
            return False, "Processo não encontrado; solicite uma nova listagem."
        actual_name = rows[0]["name"]
        if not expected_name or actual_name.casefold() != expected_name.casefold():
            return False, "O processo mudou desde a aprovação; solicite uma nova listagem."
        try:
            result = subprocess.run(
                ["taskkill.exe", "/PID", str(pid)],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"Não foi possível encerrar o processo: {exc}"
        message = (result.stdout or result.stderr).strip()
        if result.returncode != 0:
            return False, message or "O Windows recusou o encerramento normal do processo."
        return True, f"Programa encerrado normalmente: {actual_name} (PID {pid})."

    try:
        import psutil

        process = psutil.Process(pid)
        actual_name = process.name()
        if not expected_name or actual_name.casefold() != expected_name.casefold():
            return False, "O processo mudou desde a aprovação; solicite uma nova listagem."
        process.terminate()
        process.wait(timeout=5)
        return True, f"Programa encerrado normalmente: {actual_name} (PID {pid})."
    except Exception as exc:
        return False, f"Não foi possível encerrar o processo: {exc}"


def _windows_processes(pid: int | None = None) -> list[dict[str, Any]]:
    """Enumerate processes through Win32, avoiding blocked shell commands."""

    class ProcessEntry32W(ctypes.Structure):
        _fields_ = [
            ("size", ctypes.c_ulong),
            ("usage", ctypes.c_ulong),
            ("process_id", ctypes.c_ulong),
            ("default_heap_id", ctypes.c_size_t),
            ("module_id", ctypes.c_ulong),
            ("threads", ctypes.c_ulong),
            ("parent_process_id", ctypes.c_ulong),
            ("priority_base", ctypes.c_long),
            ("flags", ctypes.c_ulong),
            ("executable", ctypes.c_wchar * 260),
        ]

    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_snapshot = kernel32.CreateToolhelp32Snapshot
        create_snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
        create_snapshot.restype = ctypes.c_void_p
        process_first = kernel32.Process32FirstW
        process_first.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessEntry32W)]
        process_first.restype = ctypes.c_int
        process_next = kernel32.Process32NextW
        process_next.argtypes = [ctypes.c_void_p, ctypes.POINTER(ProcessEntry32W)]
        process_next.restype = ctypes.c_int
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
    except (AttributeError, OSError):
        return []

    snapshot = create_snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot == ctypes.c_void_p(-1).value:
        return []

    rows: list[dict[str, Any]] = []
    entry = ProcessEntry32W()
    entry.size = ctypes.sizeof(ProcessEntry32W)
    try:
        has_entry = bool(process_first(snapshot, ctypes.byref(entry)))
        while has_entry:
            current_pid = int(entry.process_id)
            if pid is None or current_pid == pid:
                rows.append(
                    {
                        "pid": current_pid,
                        "name": entry.executable,
                        "status": "running",
                    }
                )
                if pid is not None:
                    break
            has_entry = bool(process_next(snapshot, ctypes.byref(entry)))
    finally:
        close_handle(snapshot)
    return rows


def _windows_memory_status() -> tuple[float, float] | None:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_physical", ctypes.c_ulonglong),
            ("available_physical", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("available_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("available_virtual", ctypes.c_ulonglong),
            ("available_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    try:
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    except (AttributeError, OSError):
        return None
    if not ok:
        return None
    return round(status.total_physical / 1024**3, 1), float(status.memory_load)


@ToolRegistry.register("pc_status")
class PCStatusTool(BaseTool):
    tool_id = "pc_status"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="pc_status",
            description="Inspect Windows/PC health: disk, memory, CPU and temporary-folder size. Read-only.",
            parameters={"type": "object", "properties": {}},
            category="system",
        )

    def execute(self, **params: Any) -> ToolResult:
        home = Path.home()
        disk = shutil.disk_usage(home.anchor or home)
        data: dict[str, Any] = {
            "system": f"{platform.system()} {platform.release()}",
            "disk_total_gb": round(disk.total / 1024**3, 1),
            "disk_free_gb": round(disk.free / 1024**3, 1),
        }
        if platform.system() == "Windows":
            memory = _windows_memory_status()
            if memory is not None:
                data.update(memory_total_gb=memory[0], memory_used_percent=memory[1])
        else:
            try:
                import psutil

                memory = psutil.virtual_memory()
                data.update(
                    memory_total_gb=round(memory.total / 1024**3, 1),
                    memory_used_percent=round(memory.percent, 1),
                    cpu_used_percent=round(psutil.cpu_percent(interval=0.1), 1),
                )
            except ImportError:
                data["resource_metrics"] = "psutil indisponível"

        temp_root = Path(tempfile.gettempdir())
        temp_bytes = 0
        temp_files = 0
        try:
            for item in temp_root.iterdir():
                if item.is_file():
                    temp_bytes += item.stat().st_size
                    temp_files += 1
        except OSError:
            pass
        data.update(
            temp_folder=str(temp_root),
            temp_top_level_files=temp_files,
            temp_top_level_mb=round(temp_bytes / 1024**2, 1),
        )
        return ToolResult(tool_name=self.tool_id, content=json.dumps(data, ensure_ascii=False), success=True)


@ToolRegistry.register("process_list")
class ProcessListTool(BaseTool):
    tool_id = "process_list"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="process_list",
            description=(
                "List running programs with PID and executable name. Read-only. "
                "Use this before queueing local_process_close."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional program-name filter."},
                    "limit": {"type": "integer", "description": "Maximum results, up to 50."},
                },
            },
            category="system",
        )

    def execute(self, **params: Any) -> ToolResult:
        query = str(params.get("query") or "").strip().casefold()
        limit = max(1, min(int(params.get("limit") or 25), 50))
        if platform.system() == "Windows":
            rows = _windows_processes()
        else:
            try:
                import psutil
            except ImportError:
                return ToolResult(tool_name=self.tool_id, content="psutil indisponível", success=False)
            rows = []
            for process in psutil.process_iter(["pid", "name", "status"]):
                try:
                    rows.append(
                        {
                            "pid": process.info["pid"],
                            "name": str(process.info.get("name") or ""),
                            "status": process.info.get("status"),
                        }
                    )
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    continue
        if query:
            rows = [row for row in rows if query in row["name"].casefold()]
        rows.sort(key=lambda row: (row["name"].casefold(), row["pid"]))
        return ToolResult(tool_name=self.tool_id, content=json.dumps(rows[:limit], ensure_ascii=False), success=True)


@ToolRegistry.register("folder_organizer_preview")
class FolderOrganizerPreviewTool(BaseTool):
    tool_id = "folder_organizer_preview"

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="folder_organizer_preview",
            description=(
                "Create a read-only organization preview for one folder. Returns path, counts and a snapshot_hash. "
                "To apply it, queue local_organize_folder with path and snapshot_hash for desktop approval."
            ),
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Folder to inspect."}},
                "required": ["path"],
            },
            category="filesystem",
        )

    def execute(self, **params: Any) -> ToolResult:
        try:
            plan = build_folder_organization_plan(str(params.get("path") or ""))
        except (OSError, RuntimeError, ValueError) as exc:
            return ToolResult(tool_name=self.tool_id, content=str(exc), success=False)
        return ToolResult(tool_name=self.tool_id, content=json.dumps(plan, ensure_ascii=False), success=True)


__all__ = [
    "FolderOrganizerPreviewTool",
    "PCStatusTool",
    "ProcessListTool",
    "build_folder_organization_plan",
    "execute_folder_organization",
    "execute_graceful_process_close",
]
