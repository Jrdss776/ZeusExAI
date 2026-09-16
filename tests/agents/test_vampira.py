"""Tests for Vampira's shared runtime behavior."""

from openjarvis.agents.vampira import (
    VAMPIRA_IMPORTANT_EMAIL_POLICY,
    VAMPIRA_POLICY_VERSION,
    VAMPIRA_SYSTEM_PROMPT,
    canonical_vampira_config,
    migrate_vampira_agent,
    runtime_system_prompt,
)
from openjarvis.agents.vampira_agent import (
    _count_response,
    _is_count_query,
    _read_sources,
)


def _vampira(prompt: str) -> dict:
    return {
        "name": "Vampira",
        "agent_type": "simple",
        "config": {"system_prompt": prompt},
    }


def test_runtime_prompt_adds_important_email_policy() -> None:
    prompt = runtime_system_prompt(
        _vampira("Você é uma agente leve de produtividade.")
    )

    assert VAMPIRA_IMPORTANT_EMAIL_POLICY in prompt
    assert "HUD e no WhatsApp" in prompt
    assert "Sr. Jair, este e-mail precisa de resposta." in prompt
    assert "não há novos e-mails que precisem da sua atenção" in prompt
    assert "não arquive, não exclua" in prompt
    assert "Sr. Jair, encontrei estes compromissos na sua agenda" in prompt
    assert "deseja que eu prepare esta alteração na agenda" in prompt
    assert "não há compromissos que precisem da sua atenção" in prompt


def test_runtime_prompt_does_not_duplicate_policy() -> None:
    base = f"Você é uma agente leve de produtividade.\n{VAMPIRA_IMPORTANT_EMAIL_POLICY}"

    assert runtime_system_prompt(_vampira(base)).count(
        VAMPIRA_IMPORTANT_EMAIL_POLICY
    ) == 1


def test_runtime_prompt_does_not_change_other_agents() -> None:
    agent = {
        "name": "James",
        "agent_type": "simple",
        "config": {"system_prompt": "Be helpful."},
    }

    assert runtime_system_prompt(agent) == "Be helpful."


def test_canonical_config_is_server_owned_and_shares_active_model() -> None:
    config = canonical_vampira_config(
        {"model": "old-model", "tools": ["custom_tool"], "temperature": 0.2}
    )

    assert config["model"] == ""
    assert config["inherit_active_model"] is True
    assert config["system_prompt"] == VAMPIRA_SYSTEM_PROMPT
    assert config["vampira_policy_version"] == VAMPIRA_POLICY_VERSION
    assert config["tools"] == [
        "custom_tool",
        "digest_collect",
        "queue_action",
        "get_pending_actions",
    ]
    assert config["temperature"] == 0.2


def test_legacy_vampira_migration_is_idempotent() -> None:
    class Manager:
        def __init__(self) -> None:
            self.agent = {
                "id": "v1",
                "name": "My Assistant",
                "agent_type": "simple",
                "config": {
                    "model": "old-model",
                    "system_prompt": "Você é uma agente leve de produtividade.",
                },
            }
            self.updates = 0

        def list_agents(self):
            return [self.agent]

        def update_agent(self, _agent_id, **kwargs):
            self.updates += 1
            self.agent = {**self.agent, **kwargs}
            return self.agent

    manager = Manager()

    migrated = migrate_vampira_agent(manager)
    migrated_again = migrate_vampira_agent(manager)

    assert migrated["name"] == "Vampira"
    assert migrated["agent_type"] == "vampira"
    assert migrated["config"]["inherit_active_model"] is True
    assert migrated_again == migrated
    assert manager.updates == 1


def test_vampira_read_sources_selects_only_requested_connectors() -> None:
    assert _read_sources("Consulte meus e-mails recentes e tarefas pendentes") == [
        "gmail",
        "google_tasks",
    ]


def test_vampira_read_sources_skips_non_read_requests() -> None:
    assert _read_sources("Envie um e-mail para o fornecedor") == []


def test_vampira_count_query_detection() -> None:
    assert _is_count_query("Informe a quantidade de tarefas pendentes") is True
    assert _is_count_query("Resuma minhas tarefas pendentes") is False


def test_vampira_count_response_contains_only_aggregates() -> None:
    response = _count_response(
        ["gmail", "gcalendar", "google_tasks"],
        {"source_counts": {"gmail": 4, "gcalendar": 1, "google_tasks": 2}},
    )

    assert response.startswith("Sr. Jair, verifiquei seus conectores:")
    assert "E-mails recentes (últimas 24 horas): 4." in response
    assert "Compromissos de hoje: 1." in response
    assert "Tarefas pendentes: 2." in response


def test_count_questions_consult_connector_without_model(monkeypatch) -> None:
    import json
    from types import SimpleNamespace
    from unittest.mock import Mock

    from openjarvis.agents.operative import OperativeAgent
    from openjarvis.agents.vampira_agent import VampiraAgent

    model_path = Mock(side_effect=AssertionError('Count query reached model'))
    monkeypatch.setattr(OperativeAgent, 'run', model_path)
    for question, source in (
        ('Quantos e-mails tenho?', 'gmail'),
        ('Quantas tarefas tenho?', 'google_tasks'),
        ('Qual o número de compromissos hoje?', 'gcalendar'),
    ):
        agent = object.__new__(VampiraAgent)
        agent._tools = [SimpleNamespace(spec=SimpleNamespace(name='digest_collect'))]
        collected = SimpleNamespace(metadata={'source_counts': {source: 7}})
        agent._executor = Mock()
        agent._executor.execute.return_value = collected
        agent._emit_turn_start = Mock()
        agent._emit_turn_end = Mock()

        result = agent.run(question)

        agent._executor.execute.assert_called_once()
        call = agent._executor.execute.call_args.args[0]
        assert call.name == 'digest_collect'
        arguments = json.loads(call.arguments)
        assert arguments['sources'] == [source]
        assert arguments['count_only'] is True
        assert ': 7.' in result.content
        assert result.tool_results == [collected]
    model_path.assert_not_called()
