from pathlib import Path

import pytest

from openjarvis.zeusex.intelligent_memory import IntelligentMemoryStore


def test_remember_and_list_by_category(tmp_path: Path) -> None:
    store = IntelligentMemoryStore(tmp_path / "zeusex.db")
    saved = store.remember(
        "Priorizar produtos com margem acima de 20%.",
        category="decision",
        project="Achadinhos do JR",
        importance=5,
    )

    items = store.list(category="decision")

    assert saved.id > 0
    assert items == [saved]
    assert items[0].project == "Achadinhos do JR"


def test_list_filters_by_project_and_orders_importance(tmp_path: Path) -> None:
    store = IntelligentMemoryStore(tmp_path / "zeusex.db")
    store.remember("Preferência geral", category="preference", importance=2)
    store.remember("Decisão crítica", category="decision", project="ZeusExAI", importance=5)
    store.remember("Outra decisão", category="decision", project="ZeusExAI", importance=3)

    items = store.list(project="ZeusExAI")

    assert [item.content for item in items] == ["Decisão crítica", "Outra decisão"]


def test_search_finds_content_and_project(tmp_path: Path) -> None:
    store = IntelligentMemoryStore(tmp_path / "zeusex.db")
    store.remember("Usar integração local", category="project", project="Android")

    assert store.search("integração")[0].project == "Android"
    assert store.search("Android")[0].content == "Usar integração local"


def test_validates_category_importance_and_content(tmp_path: Path) -> None:
    store = IntelligentMemoryStore(tmp_path / "zeusex.db")

    with pytest.raises(ValueError, match="Categoria inválida"):
        store.remember("Teste", category="unknown")
    with pytest.raises(ValueError, match="entre 1 e 5"):
        store.remember("Teste", importance=6)
    with pytest.raises(ValueError, match="não pode ficar vazio"):
        store.remember("   ")


def test_uses_separate_table_without_breaking_legacy_database(tmp_path: Path) -> None:
    database = tmp_path / "zeusex.db"
    store = IntelligentMemoryStore(database)
    store.remember("Memória estruturada", category="general")

    assert database.exists()
    assert store.list()[0].content == "Memória estruturada"
