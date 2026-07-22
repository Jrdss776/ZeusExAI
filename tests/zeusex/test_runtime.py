"""Testes do runtime oficial do ZeusExAI."""

from __future__ import annotations

from openjarvis.zeusex.runtime import CallableEngine, RuntimeConfig, ZeusRuntime
from openjarvis.zeusex.skills import Skill, SkillRegistry


def test_runtime_persists_memories(tmp_path) -> None:
    config = RuntimeConfig(data_dir=tmp_path, history_limit=4)
    runtime = ZeusRuntime(config=config)

    assert runtime.remember("comprar ração") == "Memória registrada: comprar ração"
    reloaded = ZeusRuntime(config=config)
    assert reloaded.memories() == ["comprar ração"]


def test_runtime_releases_database_for_immediate_cleanup(tmp_path) -> None:
    data_dir = tmp_path / "runtime-close"
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=data_dir))
    runtime.remember("memória temporária")
    del runtime

    database = data_dir / "zeusex.db"
    database.unlink()
    assert database.exists() is False


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


def test_runtime_executes_skill_from_conversation(tmp_path) -> None:
    registry = SkillRegistry()
    registry.register(Skill("upper", "Converte texto.", lambda value: value.upper()))
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path), skills=registry)

    assert runtime.handle("skill upper zeus ex ai") == "ZEUS EX AI"


def test_runtime_requires_explicit_confirmation_for_sensitive_skill(tmp_path) -> None:
    registry = SkillRegistry()
    registry.register(
        Skill(
            "danger",
            "Ação sensível.",
            lambda value: f"executado: {value}",
            requires_confirmation=True,
        )
    )
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path), skills=registry)

    assert "Confirmação necessária" in runtime.handle("skill danger desligar")
    assert runtime.handle("confirmar-skill danger desligar") == "executado: desligar"


def test_runtime_converts_engine_exception_to_safe_message(tmp_path) -> None:
    def fail(prompt: str, history: list[tuple[str, str]]) -> str:
        del prompt, history
        raise ConnectionError("segredo interno")

    runtime = ZeusRuntime(
        engine=CallableEngine(fail),
        config=RuntimeConfig(data_dir=tmp_path),
    )

    response = runtime.handle("Olá")
    assert "Não consegui acessar o motor de IA" in response
    assert "ConnectionError" in response
    assert "segredo interno" not in response
