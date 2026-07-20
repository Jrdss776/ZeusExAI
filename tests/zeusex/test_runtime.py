"""Testes do runtime oficial do ZeusExAI."""

from __future__ import annotations

from openjarvis.zeusex.runtime import CallableEngine, RuntimeConfig, ZeusRuntime


def test_runtime_persists_memories(tmp_path) -> None:
    config = RuntimeConfig(data_dir=tmp_path, history_limit=4)
    runtime = ZeusRuntime(config=config)

    assert runtime.remember("comprar ração") == "Memória registrada: comprar ração"

    reloaded = ZeusRuntime(config=config)
    assert reloaded.memories() == ["comprar ração"]


def test_runtime_delegates_to_engine_and_saves_history(tmp_path) -> None:
    captured: dict[str, object] = {}

    def generate(prompt: str, history: list[tuple[str, str]]) -> str:
        captured["prompt"] = prompt
        captured["history"] = history
        return "Resposta do motor"

    runtime = ZeusRuntime(
        engine=CallableEngine(generate),
        config=RuntimeConfig(data_dir=tmp_path, history_limit=6),
    )

    assert runtime.handle("Olá Zeus", mode="assistant") == "Resposta do motor"
    assert "Usuário: Olá Zeus" in str(captured["prompt"])
    assert runtime.recent_history() == [
        ("user", "Olá Zeus"),
        ("assistant", "Resposta do motor"),
    ]


def test_runtime_handles_local_commands_without_engine(tmp_path) -> None:
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path))

    assert "ZeusExAI online" in runtime.handle("status", mode="system")
    assert "status" in runtime.handle("ajuda")
    assert runtime.handle("lembrar reunião às 15h").startswith("Memória registrada")
    assert "reunião às 15h" in runtime.handle("memoria")
