"""Testes do ranking auditável de oportunidades comerciais."""

from decimal import Decimal

import pytest

from openjarvis.zeusex.commercial_analysis import (
    CommercialAnalysisRequest,
    CommercialAnalysisService,
    CommercialCosts,
)
from openjarvis.zeusex.commercial_opportunities import (
    assess_opportunity,
    rank_opportunities,
    recommend_price,
)
from openjarvis.zeusex.marketplace import PotentialSignals


def _analyze(
    *,
    listing_id: int,
    price: str,
    product_cost: str,
    signals: PotentialSignals | None = None,
    competitors: tuple[dict[str, object], ...] = (),
):
    return CommercialAnalysisService().analyze(
        CommercialAnalysisRequest(
            marketplace="shopee",
            listing={"item_id": listing_id, "name": f"Produto {listing_id}", "price": price},
            costs=CommercialCosts(
                product_cost=Decimal(product_cost),
                marketplace_fee_percent=Decimal("10"),
            ),
            signals=signals,
            competitors=competitors,
        )
    )


def test_recommends_competitor_median_when_it_preserves_target_margin() -> None:
    result = _analyze(
        listing_id=1,
        price="100",
        product_cost="50",
        competitors=(
            {"item_id": 2, "name": "A", "price": "90"},
            {"item_id": 3, "name": "B", "price": "110"},
        ),
    )

    recommendation = recommend_price(result, target_margin_percent=Decimal("20"))

    assert recommendation.minimum_target_price == Decimal("71.43")
    assert recommendation.competitor_reference == Decimal("100.00")
    assert recommendation.recommended_price == Decimal("100.00")
    assert recommendation.status == "competitivo_com_margem"


def test_never_recommends_price_below_target_margin_floor() -> None:
    result = _analyze(
        listing_id=1,
        price="80",
        product_cost="60",
        competitors=(
            {"item_id": 2, "name": "A", "price": "70"},
            {"item_id": 3, "name": "B", "price": "75"},
        ),
    )

    recommendation = recommend_price(result, target_margin_percent=Decimal("20"))

    assert recommendation.minimum_target_price == Decimal("85.71")
    assert recommendation.recommended_price == Decimal("85.71")
    assert recommendation.status == "margem_pressiona_preco"


def test_marks_missing_market_data_instead_of_inflating_classification() -> None:
    result = _analyze(listing_id=1, price="100", product_cost="40")

    assessment = assess_opportunity(result)

    assert assessment.classification == "dados_insuficientes"
    assert assessment.missing_evidence == ("sinais_de_potencial", "concorrentes")
    assert assessment.potential_component is None
    assert assessment.price_position_component is None


def test_ranks_complete_profitable_opportunity_before_unprofitable_item() -> None:
    complete = _analyze(
        listing_id=1,
        price="100",
        product_cost="35",
        signals=PotentialSignals("90", "20", "80", "85"),
        competitors=(
            {"item_id": 11, "name": "A", "price": "95"},
            {"item_id": 12, "name": "B", "price": "105"},
        ),
    )
    unprofitable = _analyze(
        listing_id=2,
        price="50",
        product_cost="60",
        signals=PotentialSignals("90", "20", "80", "85"),
        competitors=(
            {"item_id": 21, "name": "A", "price": "45"},
            {"item_id": 22, "name": "B", "price": "55"},
        ),
    )

    ranking = rank_opportunities((unprofitable, complete))

    assert ranking[0].listing_id == "1"
    assert ranking[0].classification in {"alto", "moderado", "baixo"}
    assert ranking[1].classification == "inviavel"


def test_rejects_impossible_target_margin() -> None:
    result = _analyze(listing_id=1, price="100", product_cost="40")

    with pytest.raises(ValueError, match="somar menos de 100"):
        recommend_price(result, target_margin_percent=Decimal("90"))
