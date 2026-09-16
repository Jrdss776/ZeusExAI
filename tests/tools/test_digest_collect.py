"""Tests for the digest_collect tool."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from openjarvis.connectors._stubs import Document
from openjarvis.core.registry import ConnectorRegistry, ToolRegistry


def test_digest_collect_registered():
    from openjarvis.tools.digest_collect import DigestCollectTool

    ToolRegistry.register_value("digest_collect", DigestCollectTool)
    assert ToolRegistry.contains("digest_collect")


def test_digest_collect_executes():
    from openjarvis.tools.digest_collect import DigestCollectTool

    tool = DigestCollectTool()

    mock_docs = [
        Document(
            doc_id="test-1",
            source="gmail",
            doc_type="email",
            content="Meeting at 3pm",
            title="Team standup",
            author="alice@example.com",
            timestamp=datetime(2026, 4, 1, 10, 0),
        )
    ]

    mock_connector = MagicMock()
    mock_connector.return_value.is_connected.return_value = True
    mock_connector.return_value.sync.return_value = mock_docs

    with patch.object(ConnectorRegistry, "contains", return_value=True):
        with patch.object(ConnectorRegistry, "get", return_value=mock_connector):
            result = tool.execute(sources=["gmail"], hours_back=24)

    assert result.success is True
    assert "=== MESSAGES ===" in result.content
    assert "[gmail id=test-1] From: alice@example.com" in result.content
    assert "Team standup" in result.content
    assert result.metadata["total_items"] == 1


def test_digest_collect_missing_connector():
    from openjarvis.tools.digest_collect import DigestCollectTool

    tool = DigestCollectTool()

    with patch.object(ConnectorRegistry, "contains", return_value=False):
        result = tool.execute(sources=["nonexistent"])

    assert result.success is True  # Partial success
    assert "not available" in result.content


def test_today_calendar_uses_local_date_and_preserves_all_day_dates():
    from datetime import timedelta, timezone
    from openjarvis.tools.digest_collect import DigestCollectTool

    local = timezone(timedelta(hours=-3))
    # At noon in Sao Paulo, 01:00 UTC is yesterday locally; tomorrow at
    # 01:00 UTC is still today locally. All-day dates must not shift.
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            current = cls(2026, 9, 15, 12, tzinfo=local)
            return current.astimezone(tz) if tz is not None else current

        def astimezone(self, tz=None):
            return super().astimezone(tz or local)

    timestamps = [
        ("yesterday-utc", datetime(2026, 9, 15, 1, tzinfo=timezone.utc)),
        ("today-utc", datetime(2026, 9, 16, 1, tzinfo=timezone.utc)),
        ("today-local", datetime(2026, 9, 15, 15, tzinfo=local)),
        ("all-day", datetime(2026, 9, 15)),
        ("tomorrow-all-day", datetime(2026, 9, 16)),
    ]
    docs = [Document(doc_id=name, source="gcalendar", doc_type="event",
                     title=name, content=name, timestamp=stamp)
            for name, stamp in timestamps]
    connector = MagicMock()
    connector.return_value.is_connected.return_value = True
    connector.return_value.sync.return_value = docs
    with patch.object(ConnectorRegistry, "contains", return_value=True), patch.object(
        ConnectorRegistry, "get", return_value=connector
    ), patch("openjarvis.tools.digest_collect.datetime", FixedDateTime):
        result = DigestCollectTool().execute(sources=["gcalendar"], today_calendar_only=True)
    assert result.metadata["source_counts"] == {"gcalendar": 3}
    assert "[gcalendar] today-utc" in result.content
    assert "[gcalendar] today-local" in result.content
    assert "[gcalendar] all-day" in result.content
    assert "[gcalendar] yesterday-utc" not in result.content
    assert "[gcalendar] tomorrow-all-day" not in result.content
