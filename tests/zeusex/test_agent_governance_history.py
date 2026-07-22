from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from openjarvis.zeusex.agent_governance_history import AgentGovernanceHistory
from openjarvis.zeusex.agent_governance_history_api import AgentGovernanceHistoryAPI


@dataclass
class Plan:
    status: str
    created_at: str


@dataclass
class Receipt:
    status: str
    executed_at: str


@dataclass
class Event:
    event: str
    action: str
    created_at: str


class Queue:
    def list(self, *, limit=500):
        return [
            Plan("pending", "2026-07-20T10:00:00+00:00"),
            Plan("approved", "2026-07-19T10:00:00+00:00"),
            Plan("expired", "2025-01-01T10:00:00+00:00"),
        ][:limit]


class Executor:
    def list_receipts(self, *, limit=200):
        return [
            Receipt("succeeded", "2026-07-20T11:00:00+00:00"),
            Receipt("failed", "2026-07-19T11:00:00+00:00"),
        ][:limit]


class Audit:
    def list(self, *, limit=500):
        return [
            Event("blocked", "filesystem.list_directory", "2026-07-20T12:00:00+00:00"),
            Event("failed", "system.information", "2026-07-19T12:00:00+00:00"),
            Event("timeout", "system.information", "2026-07-19T13:00:00+00:00"),
        ][:limit]


def make_history(monkeypatch):
    fixed = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(AgentGovernanceHistory, "_now", staticmethod(lambda: fixed))
    return AgentGovernanceHistory(Queue(), Executor(), Audit())


def test_builds_read_only_history_report(monkeypatch):
    report = make_history(monkeypatch).build(days=7)
    data = report.to_dict()
    assert data["read_only"] is True
    assert data["external_actions_enabled"] is False
    assert data["period"]["days"] == 7
    assert data["totals"] == {
        "plans": 2,
        "executions": 2,
        "audit_events": 3,
        "blocked": 1,
        "failed": 1,
        "timeouts": 1,
    }


def test_groups_history_by_status_event_action_and_day(monkeypatch):
    report = make_history(monkeypatch).build(days=7)
    assert report.plans_by_status == {"approved": 1, "pending": 1}
    assert report.executions_by_status == {"failed": 1, "succeeded": 1}
    assert report.audit_by_event == {"blocked": 1, "failed": 1, "timeout": 1}
    assert report.audit_by_action == {
        "filesystem.list_directory": 1,
        "system.information": 2,
    }
    assert [item["date"] for item in report.daily] == ["2026-07-19", "2026-07-20"]
    assert report.daily[0]["timeouts"] == 1
    assert report.daily[1]["blocked"] == 1


@pytest.mark.parametrize("days", [0, 366])
def test_rejects_invalid_period(monkeypatch, days):
    with pytest.raises(ValueError):
        make_history(monkeypatch).build(days=days)


def test_api_is_strictly_read_only(monkeypatch):
    api = AgentGovernanceHistoryAPI(make_history(monkeypatch))
    assert api.status()["mode"] == "read_only"
    assert api.report(days=7)["totals"]["plans"] == 2
    with pytest.raises(PermissionError):
        api.approve(1)
    with pytest.raises(PermissionError):
        api.execute(1)
