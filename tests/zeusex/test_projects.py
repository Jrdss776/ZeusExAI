from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.orchestrator import CommandDomain, CommandOrchestrator
from openjarvis.zeusex.project_api import ProjectAPIService
from openjarvis.zeusex.project_service import ProjectService
from openjarvis.zeusex.projects import ProjectStore


def build_service(tmp_path):
    database = tmp_path / "zeusex.db"
    return ProjectService(ProjectStore(database), IntelligentMemoryStore(database))


def test_create_project_and_list(tmp_path):
    service = build_service(tmp_path)
    project = service.create_project(
        "ZeusExAI",
        description="Assistente modular",
        objective="Concluir a Fase 15",
        status="active",
    )

    assert project.name == "ZeusExAI"
    assert project.status == "active"
    assert service.projects.list_projects()[0].id == project.id


def test_project_creation_registers_memory(tmp_path):
    service = build_service(tmp_path)
    service.create_project("Shopee", objective="Aumentar conversão")

    memories = service.memories.list(project="Shopee")
    assert len(memories) == 1
    assert memories[0].category == "project"
    assert "Aumentar conversão" in memories[0].content


def test_add_and_order_tasks_by_priority(tmp_path):
    service = build_service(tmp_path)
    project = service.create_project("ZeusExAI")
    service.add_task(project.id, "Documentar", priority="medium")
    service.add_task(project.id, "Corrigir falha crítica", priority="critical")

    tasks = service.projects.list_tasks(project.id)
    assert [task.priority for task in tasks] == ["critical", "medium"]


def test_high_priority_task_registers_memory(tmp_path):
    service = build_service(tmp_path)
    project = service.create_project("ZeusExAI")
    service.add_task(project.id, "Validar CI", priority="high")

    memories = service.memories.list(project="ZeusExAI")
    assert any("Validar CI" in memory.content for memory in memories)


def test_record_project_decision(tmp_path):
    service = build_service(tmp_path)
    project = service.create_project("ZeusExAI")
    memory_id = service.record_decision(project.id, "Manter compatibilidade com OpenJarvis")

    memory = service.memories.get(memory_id)
    assert memory.category == "decision"
    assert memory.project == "ZeusExAI"


def test_update_statuses(tmp_path):
    service = build_service(tmp_path)
    project = service.create_project("ZeusExAI")
    task = service.add_task(project.id, "Implementar dashboard")

    assert service.projects.update_project_status(project.id, "active").status == "active"
    assert service.projects.update_task_status(task.id, "in_progress").status == "in_progress"


def test_duplicate_project_name_is_rejected(tmp_path):
    service = build_service(tmp_path)
    service.create_project("ZeusExAI")

    try:
        service.create_project("zeusexai")
    except ValueError as exc:
        assert "Já existe" in str(exc)
    else:
        raise AssertionError("Nome duplicado deveria ser rejeitado")


def test_project_api_flow(tmp_path):
    api = ProjectAPIService(build_service(tmp_path))
    created = api.dispatch(
        "POST",
        "/v1/projects",
        {"name": "ZeusExAI", "objective": "Concluir roadmap", "status": "active"},
    )
    project_id = created.body["project"]["id"]

    task = api.dispatch(
        "POST",
        f"/v1/projects/{project_id}/tasks",
        {"title": "Criar painel", "priority": "high"},
    )
    detail = api.dispatch("GET", f"/v1/projects/{project_id}")

    assert created.status == 201
    assert task.status == 201
    assert detail.status == 200
    assert detail.body["tasks"][0]["title"] == "Criar painel"
    assert detail.body["memories"]


def test_project_api_has_no_delete_route(tmp_path):
    api = ProjectAPIService(build_service(tmp_path))
    response = api.dispatch("DELETE", "/v1/projects/1")
    assert response.status == 404


def test_orchestrator_routes_project_commands():
    orchestrator = CommandOrchestrator()
    decision = orchestrator.route("Adicionar tarefa ao projeto ZeusExAI")
    assert decision.domain is CommandDomain.PROJECT
