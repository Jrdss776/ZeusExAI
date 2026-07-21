"""Testes da ingestão segura de respostas de marketplaces."""

import pytest

from openjarvis.zeusex.marketplace_ingestion import MarketplaceIngestionService


def test_ingests_shopee_data_items_envelope() -> None:
    batch = MarketplaceIngestionService().ingest(
        "shopee",
        {
            "data": {
                "items": [
                    {"item_id": 1, "name": "Produto A", "price": "19.90"},
                    {"item_id": 2, "name": "Produto B", "price": "29.90"},
                ]
            }
        },
    )

    assert batch.marketplace == "shopee"
    assert batch.envelope == "data.items"
    assert batch.count == 2
    assert batch.listings[0].listing_id == "1"


def test_ingests_mercado_livre_results_envelope() -> None:
    batch = MarketplaceIngestionService().ingest(
        "mercado livre",
        {
            "results": [
                {"id": "MLB1", "title": "Produto A", "price": 50},
                {"id": "MLB2", "title": "Produto B", "price": 60},
            ]
        },
    )

    assert batch.marketplace == "mercado_livre"
    assert batch.envelope == "results"
    assert batch.count == 2
    assert batch.listings[1].listing_id == "MLB2"


def test_ingests_single_listing_without_inventing_metrics() -> None:
    batch = MarketplaceIngestionService().ingest(
        "shopee",
        {"item_id": 1, "name": "Produto", "price": "25"},
    )

    assert batch.envelope == "single"
    assert batch.count == 1
    assert batch.listings[0].sold_count is None
    assert batch.listings[0].rating is None
    assert batch.listings[0].review_count is None


def test_rejects_unknown_envelope() -> None:
    with pytest.raises(ValueError, match="Resposta Shopee não reconhecida"):
        MarketplaceIngestionService().ingest("shopee", {"products": []})


def test_rejects_non_list_collection() -> None:
    with pytest.raises(ValueError, match="items precisa conter uma lista"):
        MarketplaceIngestionService().ingest("shopee", {"items": {}})


def test_reports_invalid_record_position() -> None:
    with pytest.raises(ValueError, match="posição 1"):
        MarketplaceIngestionService().ingest(
            "mercado_livre",
            {
                "results": [
                    {"id": "MLB1", "title": "Válido", "price": 10},
                    {"id": "MLB2", "price": 20},
                ]
            },
        )


def test_rejects_unknown_marketplace_before_parsing_payload() -> None:
    with pytest.raises(ValueError, match="Marketplace suportado"):
        MarketplaceIngestionService().ingest("amazon", {})
