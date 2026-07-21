from __future__ import annotations

from dataclasses import dataclass

import pytest

from openjarvis.zeusex.agent_governance_dashboard import AgentGovernanceDashboard
from openjarvis.zeusex.agent_governance_dashboard_api import AgentGovernanceDashboardAPI
from openjarvis.zeusex.execution_policy import ActionExecutionPolicy


@dataclass
class Item:
    status: str = "pending"
    event: str = "blocked"
    action: str = "system.information"

    def to_dict(self):
        return self.__dict__.copy()


class Queue:
    def list(self, *, limit=50):
        return [Item("pending"), Item("approved"), Item("rejected"), Item("expired")][:limit]


class Executor:
    def list_receipts(self, *, limit=50):
        return [Item(status="succeeded")][:limit]


class Audit:
    def list(self, *, limit=50):
        return [Item(event="blocked"), Item(event="failed"), Item(event="timeout")][:limit]


def make_dashboard():
    return AgentGovernanceDashboard(
        Queue(),
        Executor(),
        Audit(),
        {"system.information": ActionExecutionPolicy("system.information", 3, 30, 2.0, 0)},
    )


def test_builds_read_only_governance_snapshot():
    snapshot = make_dashboard().build()
    data = snapshot.to_dict()
    assert data["read_only"] is True
    assert data["can_approve"] is False
    assert data["can_execute"] is False
    assert data["external_actions_enabled"] is False


def test_summarizes_queue_receipts_policies_and_audit():
    summary = make_dashboard().build().summary
    assert summary["plans_visible"] == 4
    assert summary["plans_pending"] == 1
    assert summary["plans_approved"] == 1
    assert summary["plans_rejected"] == 1
    assert summary["plans_expired"] == 1
    assert summary["receipts_visible"] == 1
    assert summary["policies_total"] == 1
    assert summary["audit_events_visible"] == 3


def test_emits_governance_alerts():
    codes = {item.code for item in make_dashboard().build().alerts}
    assert codes == {
        "pending_reviews",
        "blocked_executions",
        "failed_executions",
        "execution_timeouts",
    }


def test_limit_is_bounded():
    snapshot = make_dashboard().build(limit=1)
    assert len(snapshot.queue) == 1
    assert len(snapshot.receipts) == 1
    assert len(snapshot.audit_events) == 1


def test_api_is_read_only():
    api = AgentGovernanceDashboardAPI(make_dashboard())
    assert api.status()["mode"] == "read_only"
    assert api.overview()["read_only"] is True
    with pytest.raises(PermissionError):
        api.approve(1)
    with pytest.raises(PermissionError):
        api.execute(1)
