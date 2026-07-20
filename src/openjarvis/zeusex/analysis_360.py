"""Relatório comercial 360 do ZeusEXai."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence
import json

from openjarvis.zeusex.competitors import CompetitorComparison, compare_listings
from openjarvis.zeusex.marketplace import (
    AdvertisementDraft,
    PotentialAnalysis,
    PotentialSignals,
    ProductInput,
    ProfitAnalysis,
    analyze_potential,
    analyze_profit,
    create_advertisement_draft,
)
from openjarvis.zeusex.marketplace_listings import NormalizedListing


def _json_safe(value: object) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Valor não serializável: {type(value).__name__}.")


@dataclass(frozen=True, slots=True)
class Analysis360Report:
    profit: ProfitAnalysis
    advertisement: AdvertisementDraft
    potential: PotentialAnalysis | None
    competitors: CompetitorComparison | None
    recommendations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def to_markdown(self) -> str:
        product = self.profit.product
        lines = [
            f"# Análise 360 — {product.name}",
            "",
            f"- Marketplace: {product.marketplace}",
            f"- Preço de venda: R$ {self.profit.revenue}",
            f"- Custos totais: R$ {self.profit.total_cost}",
            f"- Lucro estimado: R$ {self.profit.profit}",
            f"- Margem: {self.profit.margin_percent}%",
            f"- ROI: {self.profit.roi_percent}%",
            f"- Preço de equilíbrio: R$ {self.profit.break_even_price}",
            "",
            "## Potencial",
            "",
        ]
        if self.potential is None:
            lines.append("Sinais de potencial não informados.")
        else:
            lines.extend(
                [
                    f"- Pontuação: {self.potential.score}/100",
                    f"- Classificação: {self.potential.classification}",
                ]
            )

        lines.extend(["", "## Concorrência", ""])
        if self.competitors is None:
            lines.append("Anúncios concorrentes não informados.")
        else:
            known_sales = (
                str(self.competitors.known_sales_total)
                if self.competitors.known_sales_total is not None
                else "não informadas"
            )
            lines.extend(
                [
                    f"- Anúncios comparados: {self.competitors.listing_count}",
                    f"- Menor preço: R$ {self.competitors.minimum_price}",
                    f"- Maior preço: R$ {self.competitors.maximum_price}",
                    f"- Preço médio: R$ {self.competitors.average_price}",
                    f"- Preço mediano: R$ {self.competitors.median_price}",
                    f"- Vendas conhecidas somadas: {known_sales}",
                ]
            )

        lines.extend(
            [
                "",
                "## Rascunho do anúncio",
                "",
                f"**Título:** {self.advertisement.title}",
                "",
            ]
        )
        lines.extend(f"- {bullet}" for bullet in self.advertisement.bullets)
        lines.extend(
            [
                "",
                self.advertisement.description,
                "",
                "## Recomendações",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in self.recommendations)
        return "\n".join(lines).rstrip() + "\n"


def _recommendations(
    profit: ProfitAnalysis,
    potential: PotentialAnalysis | None,
    competitors: CompetitorComparison | None,
) -> tuple[str, ...]:
    items: list[str] = []
    if not profit.profitable:
        items.append("Revisar preço e custos: o lucro calculado não é positivo.")
    elif profit.margin_percent < Decimal("15"):
        items.append("Avaliar custos e preço: a margem calculada está abaixo de 15%.")
    else:
        items.append("A margem calculada é positiva; confirme todos os custos antes de publicar.")

    if profit.product.sale_price < profit.break_even_price:
        items.append("O preço informado está abaixo do preço de equilíbrio calculado.")

    if potential is None:
        items.append("Informar demanda, concorrência, margem e qualidade para pontuar o potencial.")
    elif potential.classification == "baixo":
        items.append("Validar demanda e diferenciação antes de ampliar investimento.")
    elif potential.inputs.listing_quality < Decimal("60"):
        items.append("Melhorar título, atributos, imagens e descrição do anúncio.")

    if competitors is None:
        items.append("Adicionar anúncios concorrentes para comparar posicionamento de preço.")
    elif profit.product.sale_price > competitors.maximum_price:
        items.append("O preço informado está acima do maior preço concorrente fornecido.")
    elif profit.product.sale_price < competitors.minimum_price:
        items.append("O preço informado está abaixo do menor concorrente; confirme a margem.")

    return tuple(items)


def build_analysis_360(
    product: ProductInput,
    *,
    attributes: Mapping[str, str] | None = None,
    signals: PotentialSignals | None = None,
    competitors: Sequence[NormalizedListing] = (),
) -> Analysis360Report:
    """Combina cálculos determinísticos sem buscar ou presumir dados."""

    profit = analyze_profit(product)
    potential = analyze_potential(signals) if signals is not None else None
    comparison = compare_listings(competitors) if competitors else None
    if comparison is not None and comparison.marketplace != product.marketplace:
        raise ValueError("Produto e concorrentes precisam pertencer ao mesmo marketplace.")
    advertisement = create_advertisement_draft(
        product.name,
        attributes or {},
        marketplace=product.marketplace,
    )
    return Analysis360Report(
        profit=profit,
        advertisement=advertisement,
        potential=potential,
        competitors=comparison,
        recommendations=_recommendations(profit, potential, comparison),
    )


def analysis_360_from_mapping(payload: Mapping[str, Any]) -> Analysis360Report:
    """Valida o formato JSON usado por CLI, fila e futuras interfaces."""

    product_data = payload.get("product")
    if not isinstance(product_data, Mapping):
        raise ValueError("Informe product como objeto.")
    attributes = payload.get("attributes") or {}
    if not isinstance(attributes, Mapping):
        raise ValueError("Informe attributes como objeto.")

    signal_data = payload.get("signals")
    if signal_data is not None and not isinstance(signal_data, Mapping):
        raise ValueError("Informe signals como objeto.")
    signals = PotentialSignals(**signal_data) if signal_data is not None else None

    competitor_data = payload.get("competitors") or []
    if not isinstance(competitor_data, list):
        raise ValueError("Informe competitors como lista.")
    competitors = []
    for item in competitor_data:
        if not isinstance(item, Mapping):
            raise ValueError("Cada concorrente precisa ser um objeto.")
        competitors.append(NormalizedListing(**item))

    product = ProductInput(**product_data)
    facts = {str(key): str(value) for key, value in attributes.items()}
    return build_analysis_360(
        product,
        attributes=facts,
        signals=signals,
        competitors=competitors,
    )


__all__ = [
    "Analysis360Report",
    "analysis_360_from_mapping",
    "build_analysis_360",
]
