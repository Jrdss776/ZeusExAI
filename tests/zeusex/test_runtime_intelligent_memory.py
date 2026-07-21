from openjarvis.zeusex.runtime import CallableEngine, RuntimeConfig, ZeusRuntime


def test_runtime_registers_and_lists_intelligent_memory(tmp_path):
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path))

    created = runtime.handle(
        "lembrar-inteligente project|ZeusExAI|5|Implementar a memória inteligente"
    )
    listed = runtime.handle("memoria-inteligente project")

    assert "Memória inteligente #" in created
    assert "Implementar a memória inteligente" in listed
    assert "projeto: ZeusExAI" in listed


def test_runtime_searches_intelligent_memory(tmp_path):
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path))
    runtime.handle("lembrar-inteligente decision|ZeusExAI|4|Manter compatibilidade com Jarvis")

    result = runtime.handle("buscar-memoria Jarvis")

    assert "Manter compatibilidade com Jarvis" in result


def test_runtime_preserves_legacy_memory(tmp_path):
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path))

    assert runtime.handle("lembrar comprar café") == "Memória registrada: comprar café"
    assert "comprar café" in runtime.handle("memoria")


def test_runtime_injects_local_memory_context_into_engine_prompt(tmp_path):
    prompts = []

    def capture(prompt, history):
        prompts.append((prompt, history))
        return "ok"

    runtime = ZeusRuntime(
        engine=CallableEngine(capture),
        config=RuntimeConfig(data_dir=tmp_path, memory_context_limit=3),
    )
    runtime.handle("lembrar-inteligente preference|-|5|Prefere respostas em português")

    assert runtime.handle("Como devo responder?") == "ok"
    assert "Memórias locais relevantes" in prompts[0][0]
    assert "Prefere respostas em português" in prompts[0][0]


def test_runtime_rejects_invalid_intelligent_memory_format(tmp_path):
    runtime = ZeusRuntime(config=RuntimeConfig(data_dir=tmp_path))

    result = runtime.handle("lembrar-inteligente conteúdo sem separadores")

    assert result.startswith("Use: lembrar-inteligente")
