"""Ranking auditável de oportunidades e recomendação conservadora de preço."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from openjarvis.zeusex.commercial_analysis import CommercialAnalysisResult

MONEY = Decimal("0.01")
SCORE = Decimal("0.01")


def _clamp_score(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), value))


def _round_score(value: Decimal) -> Decimal:
    return value.quantize(SCORE, rounding=ROUND_HALF_UP)


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class PriceRecommendation:
    """Preço mínimo para a margem-alvo e referência competitiva disponível."""

    current_price: Decimal
    minimum_target_price: Decimal
    recommended_price: Decimal
    target_margin_percent: Decimal
    competitor_reference: Decimal | None
    status: str


@dataclass(frozen=True, slots=True)
class OpportunityAssessment:
    """Pontuação de oportunidade acompanhada dos componentes utilizados."""

    listing_id: str
    title: str
    marketplace: str
    score: Decimal
    classification: str
    margin_component: Decimal
    roi_component: Decimal
    potential_component: Decimal | None
    price_position_component: Decimal | None
    missing_evidence: tuple[str, ...]
    price: PriceRecommendation


def recommend_price(
    result: CommercialAnalysisResult,
    *,
    target_margin_percent: Decimal = Decimal("20"),
) -> PriceRecommendation:
    """Calcula preço conservador sem ficar abaixo da margem-alvo informada."""

    target = Decimal(str(target_margin_percent))
    if not Decimal("0") <= target < Decimal("100"):
        raise ValueError("target_margin_percent precisa estar entre 0 e 100.")

    product = result.report.profit.product
    variable_percent = product.marketplace_fee_percent + product.tax_percent + target
    if variable_percent >= Decimal("100"):
        raise ValueError("Taxas e margem-alvo precisam somar menos de 100%.")

    base_cost = product.product_cost + product.fixed_fee + product.shipping_cost
    denominator = Decimal("1") - variable_percent / Decimal("100")
    minimum_target = _money(base_cost / denominator)

    comparison = result.report.competitors
    competitor_reference = comparison.median_price if comparison is not None else None
    if competitor_reference is None:
        recommended = max(product.sale_price, minimum_target)
        status = "sem_referencia_concorrente"
    elif competitor_reference >= minimum_target:
        recommended = competitor_reference
        status = "competitivo_com_margem"
    else:
        recommended = minimum_target
        status = "margem_pressiona_preco"

    return PriceRecommendation(
        current_price=_money(product.sale_price),
        minimum_target_price=minimum_target,
        recommended_price=_money(recommended),
        target_margin_percent=_round_score(target),
        competitor_reference=(
            _money(competitor_reference) if competitor_reference is not None else None
        ),
        status=status,
    )


def assess_opportunity(
    result: CommercialAnalysisResult,
    *,
    target_margin_percent: Decimal = Decimal("20"),
) -> OpportunityAssessment:
    """Pontua apenas métricas calculadas e sinais explicitamente fornecidos."""

    profit = result.report.profit
    margin_component = _clamp_score(profit.margin_percent)
    roi_component = _clamp_score(profit.roi_percent)

    potential = result.report.potential
    potential_component = potential.score if potential is not None else None

    comparison = result.report.competitors
    price_position_component: Decimal | None = None
    if comparison is not None:
        sale_price = profit.product.sale_price
        if comparison.minimum_price <= sale_price <= comparison.maximum_price:
            price_position_component = Decimal("100")
        elif sale_price < comparison.minimum_price:
            price_position_component = Decimal("70")
        else:
            price_position_component = Decimal("40")

    weighted = margin_component * Decimal("0.35") + roi_component * Decimal("0.25")
    missing: list[str] = []
    if potential_component is None:
        missing.append("sinais_de_potencial")
    else:
        weighted += potential_component * Decimal("0.30")
    if price_position_component is None:
        missing.append("concorrentes")
    else:
        weighted += price_position_component * Decimal("0.10")

    score = _round_score(weighted)
    if not profit.profitable:
        classification = "inviavel"
    elif missing:
        classification = "dados_insuficientes"
    elif score >= Decimal("75"):
        classification = "alto"
    elif score >= Decimal("50"):
        classification = "moderado"
    else:
        classification = "baixo"

    return OpportunityAssessment(
        listing_id=result.listing.listing_id,
        title=result.listing.title,
        marketplace=result.listing.marketplace,
        score=score,
        classification=classification,
        margin_component=_round_score(margin_component),
        roi_component=_round_score(roi_component),
        potential_component=(
            _round_score(potential_component) if potential_component is not None else None
        ),
        price_position_component=price_position_component,
        missing_evidence=tuple(missing),
        price=recommend_price(result, target_margin_percent=target_margin_percent),
    )


def rank_opportunities(
    results: Iterable[CommercialAnalysisResult],
    *,
    target_margin_percent: Decimal = Decimal("20"),
) -> tuple[OpportunityAssessment, ...]:
    """Ordena por viabilidade, nota e identificador para resultado determinístico."""

    assessments = [
        assess_opportunity(item, target_margin_percent=target_margin_percent)
        for item in results
    ]
    priority = {
        "alto": 5,
        "moderado": 4,
        "baixo": 3,
        "dados_insuficientes": 2,
        "inviavel": 1,
    }
    return tuple(
        sorted(
            assessments,
            key=lambda item: (
                -priority[item.classification],
                -item.score,
                item.listing_id,
            ),
        )
    )


__all__ = [
    "OpportunityAssessment",
    "PriceRecommendation",
    "assess_opportunity",
    "rank_opportunities",
    "recommend_price",
]
