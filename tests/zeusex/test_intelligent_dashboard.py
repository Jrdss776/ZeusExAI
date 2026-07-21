from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.dashboard_api import DashboardAPIService
from openjarvis.zeusex.goals import GoalStore
from openjarvis.zeusex.intelligent_dashboard import IntelligentDashboardService
from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.projects import ProjectStore
from openjarvis.zeusex.report_store import AnalysisReportStore


def build_dashboard(tmp_path):
    database = tmp_path / "zeusex.db"
    projects = ProjectStore(database)
    goals = GoalStore(database)
    memories = IntelligentMemoryStore(database)
    reports = AnalysisReportStore(database)
    campaigns = CampaignTemplateStore(database)
    return (
        IntelligentDashboardService(projects, goals, memories, reports, campaigns),
        projects,
        goals,
        memories,
    )


def test_empty_dashboard_has_stable_summary(tmp_path):
    dashboard, _, _, _ = build_dashboard(tmp_path)

    snapshot = dashboard.build()

    assert snapshot.summary["projects_total"] == 0
    assert snapshot.summary["goals_total"] == 0
    assert snapshot.summary["alerts_total"] == 0
    assert snapshot.priority_tasks == ()


def test_dashboard_aggregates_projects_goals_tasks_and_memories(tmp_path):
    dashboard, projects, goals, memories = build_dashboard(tmp_path)
    project = projects.create_project("ZeusExAI", status="active")
    projects.add_task(project.id, "Corrigir integração", priority="critical", status="blocked")
    goals.create_goal(
        "Finalizar dashboard",
        metric="percentual",
        baseline=0,
        target=100,
        current=10,
        project_id=project.id,
        status="active",
        unit="%",
    )
    memories.remember(
        "Dashboard deve permanecer local.",
        category="decision",
        project="ZeusExAI",
        importance=5,
    )

    snapshot = dashboard.build(limit=10)

    assert snapshot.summary["projects_active"] == 1
    assert snapshot.summary["open_tasks"] == 1
    assert snapshot.summary["blocked_tasks"] == 1
    assert snapshot.summary["goals_total"] == 1
    assert snapshot.summary["average_goal_progress"] == 10.0
    assert snapshot.priority_tasks[0]["priority"] == "critical"
    codes = {alert.code for alert in snapshot.alerts}
    assert "priority_task" in codes
    assert "goal_low_progress" in codes
    assert snapshot.recent_memories[0]["category"] == "decision"


def test_dashboard_limit_is_bounded(tmp_path):
    dashboard, projects, _, _ = build_dashboard(tmp_path)
    for index in range(60):
        projects.create_project(f"Projeto {index}")

    snapshot = dashboard.build(limit=500)

    assert len(snapshot.projects) == 50


def test_dashboard_api_is_read_only(tmp_path):
    dashboard, _, _, _ = build_dashboard(tmp_path)
    api = DashboardAPIService(dashboard)

    response = api.dispatch("GET", "/v1/dashboard", {"limit": "5"})
    blocked = api.dispatch("DELETE", "/v1/dashboard")

    assert response.status == 200
    assert response.body["ok"] is True
    assert "summary" in response.body["dashboard"]
    assert blocked.status == 404


def test_dashboard_api_rejects_invalid_limit(tmp_path):
    dashboard, _, _, _ = build_dashboard(tmp_path)
    api = DashboardAPIService(dashboard)

    response = api.dispatch("GET", "/v1/dashboard", {"limit": "invalid"})

    assert response.status == 400
    assert response.body["ok"] is False
