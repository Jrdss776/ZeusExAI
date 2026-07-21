from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore
from openjarvis.zeusex.memory_api import IntelligentMemoryAPI


def test_memory_api_creates_lists_and_searches(tmp_path):
    api = IntelligentMemoryAPI(IntelligentMemoryStore(tmp_path / "zeusex.db"))

    created = api.dispatch(
        "POST",
        "/v1/memories",
        {
            "category": "project",
            "project": "ZeusExAI",
            "importance": 5,
            "content": "Integrar a memória ao painel móvel",
        },
    )
    listed = api.dispatch(
        "GET",
        "/v1/memories",
        query={"category": "project", "project": "ZeusExAI"},
    )
    searched = api.dispatch(
        "GET",
        "/v1/memories/search",
        query={"q": "painel móvel"},
    )

    assert created.status == 201
    assert created.body["memory"]["importance"] == 5
    assert listed.status == 200
    assert len(listed.body["items"]) == 1
    assert searched.body["items"][0]["project"] == "ZeusExAI"


def test_memory_api_rejects_invalid_payload(tmp_path):
    api = IntelligentMemoryAPI(IntelligentMemoryStore(tmp_path / "zeusex.db"))

    response = api.dispatch(
        "POST",
        "/v1/memories",
        {"category": "unknown", "content": "teste"},
    )

    assert response.status == 400
    assert response.body["ok"] is False


def test_memory_api_has_no_delete_route(tmp_path):
    api = IntelligentMemoryAPI(IntelligentMemoryStore(tmp_path / "zeusex.db"))

    response = api.dispatch("DELETE", "/v1/memories/1")

    assert response.status == 404
