"""Safety contracts for the Gmail and Google Calendar agent templates."""

from __future__ import annotations

from pathlib import Path

import tomllib

from openjarvis.agents.manager import AgentManager

TEMPLATE_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "openjarvis" / "agents" / "templates"
)


def _template(name: str) -> dict:
    return tomllib.loads((TEMPLATE_DIR / name).read_text(encoding="utf-8"))["template"]


def test_gmail_assistant_is_read_first_and_never_has_direct_send_tool() -> None:
    template = _template("gmail_assistant.toml")

    assert template["tools"] == [
        "digest_collect",
        "think",
        "memory_retrieve",
        "queue_action",
    ]
    assert "channel_send" not in template["tools"]
    assert 'sources=["gmail"]' in template["system_prompt_template"]
    assert 'action_type="email_archive"' in template["system_prompt_template"]
    assert 'action_type="email_delete"' in template["system_prompt_template"]
    assert (
        'payload={{"message_id":"<message_id>"}}' in template["system_prompt_template"]
    )
    assert "gmail:<message_id>" in template["system_prompt_template"]
    assert 'tier="high"' in template["system_prompt_template"]


def test_calendar_assistant_only_queues_supported_high_risk_actions() -> None:
    template = _template("google_calendar_assistant.toml")

    assert template["tools"] == [
        "digest_collect",
        "think",
        "memory_retrieve",
        "queue_action",
    ]
    assert 'sources=["gcalendar"]' in template["system_prompt_template"]
    assert 'action_type="calendar_accept"' in template["system_prompt_template"]
    assert 'action_type="calendar_decline"' in template["system_prompt_template"]
    assert '{{"event_id":"<event_id>"' in template["system_prompt_template"]
    assert '"calendar_id":"<calendar_id>"}}' in template["system_prompt_template"]
    assert "gcalendar:<event_id>" in template["system_prompt_template"]
    assert 'tier="high"' in template["system_prompt_template"]
    assert (
        "não pode criá-lo, alterá-lo ou cancelá-lo"
        in template["system_prompt_template"]
    )


def test_legacy_inbox_triager_cannot_send_messages_directly() -> None:
    template = _template("inbox_triager.toml")

    assert "channel_send" not in template["tools"]
    assert "Never send or forward a message" in template["system_prompt_template"]


def test_manager_discovers_google_workspace_templates() -> None:
    template_ids = {template["id"] for template in AgentManager.list_templates()}

    assert {"gmail_assistant", "google_calendar_assistant"} <= template_ids


def test_manager_expands_gmail_assistant_instruction(tmp_path: Path) -> None:
    manager = AgentManager(db_path=str(tmp_path / "agents.db"))
    try:
        agent = manager.create_from_template(
            "gmail_assistant",
            "Caixa de entrada do JR",
            overrides={"instruction": "Priorize mensagens de clientes."},
        )
    finally:
        manager.close()

    config = agent["config"]
    assert "Priorize mensagens de clientes." in config["system_prompt"]
    assert 'payload={"message_id":"<message_id>"}' in config["system_prompt"]
    assert config["tools"] == [
        "digest_collect",
        "think",
        "memory_retrieve",
        "queue_action",
    ]
    assert "system_prompt_template" not in config


def test_manager_expands_calendar_assistant_instruction(tmp_path: Path) -> None:
    manager = AgentManager(db_path=str(tmp_path / "agents.db"))
    try:
        agent = manager.create_from_template(
            "google_calendar_assistant",
            "Agenda do JR",
            overrides={"instruction": "Avise sobre conflitos da próxima semana."},
        )
    finally:
        manager.close()

    config = agent["config"]
    assert "Avise sobre conflitos da próxima semana." in config["system_prompt"]
    assert (
        'payload={"event_id":"<event_id>","calendar_id":"<calendar_id>"}'
        in config["system_prompt"]
    )
    assert config["tools"] == [
        "digest_collect",
        "think",
        "memory_retrieve",
        "queue_action",
    ]
    assert "system_prompt_template" not in config
