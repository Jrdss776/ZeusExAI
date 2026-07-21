"""Testes da integração entre ingestão e análise comercial em lote."""

from decimal import Decimal

import pytest

from openjarvis.zeusex.commercial_analysis import CommercialCosts
from openjarvis.zeusex.commercial_batch import (
    CommercialBatchRequest,
    CommercialBatchService,
)
from openjarvis.zeusex.marketplace import PotentialSignals


def test_analyzes_shopee_batch_with_costs_per_listing() -> None:
    result = CommercialBatchService().analyze(
        CommercialBatchRequest(
            marketplace="shopee",
            payload={
                "items": [
                    {"item_id": 10, "name": "Produto A", "price": "100"},
                    {"item_id": 20, "name": "Produto B", "price": "80"},
                ]
            },
            costs_by_listing={
                "10": CommercialCosts(product_cost=Decimal("50")),
                "20": CommercialCosts(product_cost=Decimal("30")),
            },
        )
    )

    assert result.ingestion.envelope == "items"
    assert result.count == 2
    assert result.analyses[0].report.profit.profit == Decimal("50.00")
    assert result.analyses[1].report.profit.profit == Decimal("50.00")


def test_uses_default_costs_and_listing_specific_metadata() -> None:
    result = CommercialBatchService().analyze(
        CommercialBatchRequest(
            marketplace="mercado livre",
            payload={
                "results": [
                    {"id": "MLB1", "title": "Produto", "price": "90"}
                ]
            },
            costs_by_listing={},
            default_costs=CommercialCosts(product_cost=Decimal("40")),
            attributes_by_listing={"MLB1": {"Material": "aço"}},
            signals_by_listing={
                "MLB1": PotentialSignals("80", "20", "60", "70")
            },
        )
    )

    analysis = result.analyses[0]
    assert analysis.report.profit.profit == Decimal("50.00")
    assert analysis.report.advertisement.bullets == ("Material: aço",)
    assert analysis.report.potential is not None


def test_rejects_batch_when_listing_has_no_explicit_or_default_costs() -> None:
    request = CommercialBatchRequest(
        marketplace="shopee",
        payload={"item_id": 10, "name": "Produto", "price": "30"},
        costs_by_listing={},
    )

    with pytest.raises(ValueError, match="Custos ausentes.*10"):
        CommercialBatchService().analyze(request)


def test_empty_recognized_batch_returns_empty_analysis_tuple() -> None:
    result = CommercialBatchService().analyze(
        CommercialBatchRequest(
            marketplace="mercado_livre",
            payload={"results": []},
            costs_by_listing={},
        )
    )

    assert result.ingestion.count == 0
    assert result.analyses == ()
