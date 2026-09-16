"""Telegram start command regression tests; no network or real messages."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from openjarvis.server.agent_manager_routes import start_telegram_channel


@pytest.mark.parametrize("text,agent_type,welcome", [
    ("/start", "vampira", True),
    (" /start\n", "vampira", True),
    ("Quantos e-mails tenho?", "vampira", False),
    ("Explique /start", "vampira", False),
    ("/start extra", "vampira", False),
    ("/start", "simple", False),
])
def test_start_dispatch(text, agent_type, welcome):
    manager = Mock()
    manager.get_agent.return_value = {"agent_type": agent_type, "config": {}}
    manager.list_messages.return_value = []
    app = SimpleNamespace(state=SimpleNamespace())
    with patch("openjarvis.channels.telegram.TelegramChannel") as channel_cls, patch(
        "openjarvis.agents.executor.AgentExecutor"
    ) as executor_cls, patch(
        "openjarvis.server.agent_manager_routes._make_lightweight_system"
    ):
        channel = channel_cls.return_value
        start_telegram_channel(app, manager, "agent", "fake-token", "123")
        handler = channel.on_message.call_args.args[0]
        handler(SimpleNamespace(content=text, conversation_id="123", message_id="9"))
        if welcome:
            manager.send_message.assert_not_called()
            executor_cls.assert_not_called()
            channel.send.assert_called_once()
            args, kwargs = channel.send.call_args
            assert args[0] == "123"
            assert "Sou a Vampira" in args[1]
            assert "Não consultei" in args[1]
            assert kwargs["conversation_id"] == "9"
        else:
            manager.send_message.assert_called_once_with("agent", text, mode="immediate")
            executor_cls.return_value.execute_tick.assert_called_once_with("agent")
