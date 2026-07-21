"""Testes da rota local do modo Achadinhos do JR."""

from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.mobile_api import MobileAPIService
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


def _service(tmp_path) -> MobileAPIService:
    return MobileAPIService(
        AnalysisReportStore(tmp_path / "reports.db"),
        CampaignTemplateStore(tmp_path / "campaigns.db"),
        SafeScheduler(tmp_path / "schedule.db"),
    )


def test_local_achadinhos_route_selects_only_approved_products(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "POST",
        "/v1/achadinhos",
        {
            "marketplace": "shopee",
            "payload": {
                "items": [
                    {"item_id": 1, "name": "Produto aprovado", "price": "100"},
                    {"item_id": 2, "name": "Produto sem evidências", "price": "60"},
                ]
            },
            "costs_by_listing": {
                "1": {"product_cost": "40"},
                "2": {"product_cost": "30"},
            },
            "attributes_by_listing": {
                "1": {"Material": "aço"},
            },
            "signals_by_listing": {
                "1": {
                    "demand": "90",
                    "competition": "10",
                    "margin": "80",
                    "listing_quality": "90",
                }
            },
            "competitors_by_listing": {
                "1": [
                    {
                        "item_id": 10,
                        "name": "Concorrente",
                        "price": "95",
                    }
                ]
            },
            "catalog_by_listing": {
                "1": [
                    {
                        "name": "Produto aprovado",
                        "category": "utilidades",
                        "price": "100",
                        "complements": ["Acessório"],
                    },
                    {
                        "name": "Acessório",
                        "category": "acessórios",
                        "price": "20",
                    },
                ]
            },
        },
    )

    assert response.status == 200
    assert response.body["ok"] is True
    batch = response.body["achadinhos"]
    assert len(batch["selected"]) == 1
    assert batch["selected"][0]["opportunity"]["listing_id"] == "1"
    assert batch["selected"][0]["campaign"]["template"]["brand"] == "Achadinhos do JR"
    assert batch["selected"][0]["campaign"]["combinations"][0]["kind"] == "cross_sell"
    assert len(batch["rejected"]) == 1
    assert batch["rejected"][0]["listing_id"] == "2"
    assert batch["rejected"][0]["classification"] == "dados_insuficientes"


def test_local_achadinhos_route_respects_custom_policy(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "POST",
        "/v1/achadinhos",
        {
            "marketplace": "mercado_livre",
            "payload": {
                "results": [
                    {"id": "MLB1", "title": "Produto", "price": "100"},
                ]
            },
            "costs_by_listing": {"MLB1": {"product_cost": "40"}},
            "signals_by_listing": {
                "MLB1": {
                    "demand": "90",
                    "competition": "10",
                    "margin": "80",
                    "listing_quality": "90",
                }
            },
            "competitors_by_listing": {
                "MLB1": [
                    {"id": "MLB2", "title": "Concorrente", "price": "95"},
                ]
            },
            "policy": {
                "minimum_score": "90",
                "allowed_classifications": ["alto"],
                "maximum_items": 1,
            },
        },
    )

    assert response.status == 200
    assert response.body["achadinhos"]["selected"] == []
    assert len(response.body["achadinhos"]["rejected"]) == 1


def test_local_achadinhos_route_rejects_ambiguous_nested_values(tmp_path) -> None:
    response = _service(tmp_path).dispatch(
        "POST",
        "/v1/achadinhos",
        {
            "marketplace": "shopee",
            "payload": {"item_id": 1, "name": "Produto", "price": "50"},
            "costs_by_listing": {"1": "custo inválido"},
        },
    )

    assert response.status == 400
    assert response.body["ok"] is False
    assert "costs_by_listing.1 precisa ser um objeto" in response.body["error"]
