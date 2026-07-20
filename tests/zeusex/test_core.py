from pathlib import Path

from zeusex import ZeusAssistant, ZeusConfig
from zeusex.memory import SQLiteMemory
from zeusex.router import CommandRouter


def test_router_dispatches_registered_command() -> None:
    router = CommandRouter()
    router.register("eco", lambda argument: argument)

    result = router.dispatch("eco teste")

    assert result is not None
    assert result.command == "eco"
    assert result.response == "teste"


def test_sqlite_memory_persists_items(tmp_path: Path) -> None:
    memory = SQLiteMemory(tmp_path / "memory.db")
    memory.add("memory", "comprar ração")

    items = memory.recent()

    assert len(items) == 1
    assert items[0].role == "memory"
    assert items[0].content == "comprar ração"


def test_assistant_default_commands(tmp_path: Path) -> None:
    assistant = ZeusAssistant(ZeusConfig(data_dir=tmp_path))

    assert "ZeusExAI online" in assistant.handle("status")
    assert "Memória registrada" in assistant.handle("lembrar teste")
    assert "teste" in assistant.handle("memoria")
