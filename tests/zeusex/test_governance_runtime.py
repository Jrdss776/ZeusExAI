from __future__ import annotations

from openjarvis.zeusex.governance_runtime import build_governance_runtime_apis


def test_runtime_apis_are_available_and_read_only(tmp_path) -> None:
    runtime = build_governance_runtime_apis(tmp_path)

    dashboard_status = runtime.dashboard.status()
    history_status = runtime.history.status()
    overview = runtime.dashboard.overview()
    report = runtime.history.report(days=7)

    assert dashboard_status["enabled"] is True
    assert dashboard_status["mode"] == "read_only"
    assert dashboard_status["can_approve"] is False
    assert dashboard_status["can_execute"] is False
    assert history_status["mode"] == "read_only"
    assert overview["read_only"] is True
    assert overview["external_actions_enabled"] is False
    assert report["read_only"] is True
    assert report["external_actions_enabled"] is False


def test_runtime_apis_reuse_persistent_governance_databases(tmp_path) -> None:
    first = build_governance_runtime_apis(tmp_path)
    second = build_governance_runtime_apis(tmp_path)

    assert first.dashboard.dashboard.queue.database_path == tmp_path / "agent-plan-queue.db"
    assert second.dashboard.dashboard.queue.database_path == tmp_path / "agent-plan-queue.db"
    assert (tmp_path / "agent-plan-queue.db").is_file()
    assert (tmp_path / "agent-executions.db").is_file()
    assert (tmp_path / "agent-execution-audit.db").is_file()
    assert first.dashboard.dashboard.queue is first.history.history.queue
    assert first.dashboard.dashboard.executor is first.history.history.executor
    assert first.dashboard.dashboard.audit is first.history.history.audit
