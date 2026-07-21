"""Testes do serviço comercial unificado da Fase 14."""

from decimal import Decimal

import pytest

from openjarvis.zeusex.commercial_analysis import (
    CommercialAnalysisRequest,
    CommercialAnalysisService,
    CommercialCosts,
)
from openjarvis.zeusex.marketplace import PotentialSignals


def test_analyzes_shopee_listing_and_competitors_in_one_flow() -> None:
    result = CommercialAnalysisService().analyze(
        CommercialAnalysisRequest(
            marketplace="shopee",
            listing={"item_id": 10, "name": "Produto A", "price": "100"},
            costs=CommercialCosts(
                product_cost=Decimal("50"),
                marketplace_fee_percent=Decimal("10"),
                shipping_cost=Decimal("5"),
                tax_percent=Decimal("5"),
            ),
            attributes={"Material": "algodão"},
            signals=PotentialSignals("80", "30", "60", "70"),
            competitors=(
                {"item_id": 11, "name": "Concorrente", "price": "95"},
            ),
        )
    )

    assert result.listing.marketplace == "shopee"
    assert result.report.profit.profit == Decimal("30.00")
    assert result.report.competitors is not None
    assert result.report.competitors.minimum_price == Decimal("95.00")
    assert result.report.advertisement.bullets == ("Material: algodão",)


def test_analyzes_mercado_livre_using_its_native_field_names() -> None:
    result = CommercialAnalysisService().analyze(
        CommercialAnalysisRequest(
            marketplace="mercado livre",
            listing={"id": "MLB1", "title": "Produto B", "price": "80"},
            costs=CommercialCosts(product_cost=Decimal("35"), fixed_fee=Decimal("5")),
        )
    )

    assert result.listing.listing_id == "MLB1"
    assert result.report.profit.product.marketplace == "mercado_livre"
    assert result.report.profit.profit == Decimal("40.00")


def test_rejects_unknown_marketplace_before_reading_payload() -> None:
    request = CommercialAnalysisRequest(
        marketplace="amazon",
        listing={},
        costs=CommercialCosts(product_cost=Decimal("10")),
    )

    with pytest.raises(ValueError, match="Marketplace suportado"):
        CommercialAnalysisService().analyze(request)


def test_preserves_missing_marketplace_metrics_as_unknown() -> None:
    result = CommercialAnalysisService().analyze(
        CommercialAnalysisRequest(
            marketplace="shopee",
            listing={"item_id": 1, "name": "Produto", "price": "25"},
            costs=CommercialCosts(product_cost=Decimal("10")),
        )
    )

    assert result.listing.sold_count is None
    assert result.listing.rating is None
    assert result.listing.review_count is None
