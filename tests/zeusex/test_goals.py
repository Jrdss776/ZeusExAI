from openjarvis.zeusex.command_orchestrator import CommandDomain, CommandOrchestrator
from openjarvis.zeusex.goal_api import GoalAPIService
from openjarvis.zeusex.goal_service import GoalService
from openjarvis.zeusex.goals import GoalStore
from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.projects import ProjectStore


def build_services(tmp_path):
    database = tmp_path / "zeusex.db"
    projects = ProjectStore(database)
    memories = IntelligentMemoryStore(database)
    goals = GoalStore(database)
    service = GoalService(goals, projects, memories)
    return projects, memories, goals, service


def test_goal_progress_and_checkins(tmp_path):
    _, _, goals, service = build_services(tmp_path)
    goal = service.create_goal(
        "Aumentar vendas",
        metric="pedidos",
        baseline=100,
        target=200,
        current=120,
        unit="pedidos",
        status="active",
    )
    assert goal.progress_percent == 20.0
    service.check_in(goal.id, 150, note="Campanha ativa")
    updated = goals.get_goal(goal.id)
    assert updated.progress_percent == 50.0
    assert len(goals.list_checkins(goal.id)) == 1


def test_decrease_goal_progress(tmp_path):
    _, _, _, service = build_services(tmp_path)
    goal = service.create_goal(
        "Reduzir custo",
        metric="custo por venda",
        baseline=20,
        target=10,
        current=15,
        direction="decrease",
        unit="BRL",
    )
    assert goal.progress_percent == 50.0


def test_goal_can_be_linked_to_project_and_memory(tmp_path):
    projects, memories, _, service = build_services(tmp_path)
    project = projects.create_project("ZeusExAI")
    goal = service.create_goal(
        "Concluir fase 15",
        metric="fases concluídas",
        target=5,
        project_id=project.id,
    )
    assert goal.project_id == project.id
    assert memories.list(project="ZeusExAI")


def test_reaching_target_marks_goal_achieved(tmp_path):
    _, memories, goals, service = build_services(tmp_path)
    goal = service.create_goal("Lançar produto", metric="lançamentos", target=1)
    service.check_in(goal.id, 1, note="Publicado")
    assert goals.get_goal(goal.id).status == "achieved"
    assert any(item.category == "decision" for item in memories.list())


def test_goal_api_flow(tmp_path):
    projects, _, goals, service = build_services(tmp_path)
    project = projects.create_project("Shopee")
    api = GoalAPIService(goals, service)
    created = api.dispatch(
        "POST",
        "/v1/goals",
        {
            "title": "Aumentar margem",
            "metric": "margem",
            "target": 30,
            "baseline": 20,
            "project_id": project.id,
            "unit": "%",
        },
    )
    assert created.status == 201
    goal_id = created.body["goal"]["id"]
    checkin = api.dispatch("POST", f"/v1/goals/{goal_id}/checkins", {"value": 25})
    assert checkin.status == 201
    assert checkin.body["goal"]["progress_percent"] == 50.0
    detail = api.dispatch("GET", f"/v1/goals/{goal_id}")
    assert detail.status == 200
    assert len(detail.body["checkins"]) == 1


def test_goal_api_has_no_delete_route(tmp_path):
    _, _, goals, service = build_services(tmp_path)
    api = GoalAPIService(goals, service)
    response = api.dispatch("DELETE", "/v1/goals/1")
    assert response.status == 404


def test_orchestrator_routes_goal_commands():
    decision = CommandOrchestrator().route("registrar medição da meta de vendas")
    assert decision.domain is CommandDomain.GOAL
