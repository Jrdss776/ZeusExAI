"""Núcleo comercial determinístico do ZeusEXai para marketplaces."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping

MONEY = Decimal("0.01")
PERCENT = Decimal("0.01")
SUPPORTED_MARKETPLACES = frozenset({"shopee", "mercado_livre"})


def _decimal(value: Decimal | int | float | str) -> Decimal:
    """Converte valores financeiros sem herdar imprecisão de ponto flutuante."""

    return Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class ProductInput:
    """Dados verificáveis fornecidos pelo usuário ou por uma integração."""

    name: str
    marketplace: str
    sale_price: Decimal
    product_cost: Decimal
    marketplace_fee_percent: Decimal = Decimal("0")
    fixed_fee: Decimal = Decimal("0")
    shipping_cost: Decimal = Decimal("0")
    tax_percent: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        name = self.name.strip()
        marketplace = self.marketplace.strip().lower().replace(" ", "_")
        if not name:
            raise ValueError("O produto precisa de um nome.")
        if marketplace not in SUPPORTED_MARKETPLACES:
            raise ValueError("Marketplace suportado: shopee ou mercado_livre.")

        object.__setattr__(self, "name", name)
        object.__setattr__(self, "marketplace", marketplace)
        for field_name in (
            "sale_price",
            "product_cost",
            "marketplace_fee_percent",
            "fixed_fee",
            "shipping_cost",
            "tax_percent",
        ):
            value = _decimal(getattr(self, field_name))
            if value < 0:
                raise ValueError(f"{field_name} não pode ser negativo.")
            object.__setattr__(self, field_name, value)
        if self.sale_price <= 0:
            raise ValueError("O preço de venda precisa ser maior que zero.")
        if self.marketplace_fee_percent + self.tax_percent >= 100:
            raise ValueError("A soma das taxas percentuais precisa ser menor que 100%.")


@dataclass(frozen=True, slots=True)
class ProfitAnalysis:
    product: ProductInput
    revenue: Decimal
    marketplace_fee: Decimal
    taxes: Decimal
    total_cost: Decimal
    profit: Decimal
    margin_percent: Decimal
    roi_percent: Decimal
    break_even_price: Decimal

    @property
    def profitable(self) -> bool:
        return self.profit > 0


def analyze_profit(product: ProductInput) -> ProfitAnalysis:
    """Calcula lucro, margem, ROI e preço de equilíbrio."""

    revenue = product.sale_price
    marketplace_fee = revenue * product.marketplace_fee_percent / Decimal("100")
    taxes = revenue * product.tax_percent / Decimal("100")
    base_cost = product.product_cost + product.fixed_fee + product.shipping_cost
    total_cost = base_cost + marketplace_fee + taxes
    profit = revenue - total_cost
    margin = profit / revenue * Decimal("100")
    roi = (
        profit / base_cost * Decimal("100")
        if base_cost > 0
        else Decimal("0")
    )
    variable_rate = (
        product.marketplace_fee_percent + product.tax_percent
    ) / Decimal("100")
    break_even = base_cost / (Decimal("1") - variable_rate)

    return ProfitAnalysis(
        product=product,
        revenue=_money(revenue),
        marketplace_fee=_money(marketplace_fee),
        taxes=_money(taxes),
        total_cost=_money(total_cost),
        profit=_money(profit),
        margin_percent=_percent(margin),
        roi_percent=_percent(roi),
        break_even_price=_money(break_even),
    )


@dataclass(frozen=True, slots=True)
class PotentialSignals:
    """Sinais normalizados; nenhum valor é presumido pelo ZeusEXai."""

    demand: Decimal
    competition: Decimal
    margin: Decimal
    listing_quality: Decimal

    def __post_init__(self) -> None:
        for field_name in ("demand", "competition", "margin", "listing_quality"):
            value = _decimal(getattr(self, field_name))
            if not Decimal("0") <= value <= Decimal("100"):
                raise ValueError(f"{field_name} precisa estar entre 0 e 100.")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True, slots=True)
class PotentialAnalysis:
    score: Decimal
    classification: str
    inputs: PotentialSignals


def analyze_potential(signals: PotentialSignals) -> PotentialAnalysis:
    """Pontua potencial usando somente sinais explícitos e auditáveis."""

    score = (
        signals.demand * Decimal("0.35")
        + (Decimal("100") - signals.competition) * Decimal("0.20")
        + signals.margin * Decimal("0.30")
        + signals.listing_quality * Decimal("0.15")
    )
    rounded = _percent(score)
    if rounded >= 75:
        classification = "alto"
    elif rounded >= 50:
        classification = "moderado"
    else:
        classification = "baixo"
    return PotentialAnalysis(rounded, classification, signals)


@dataclass(frozen=True, slots=True)
class AdvertisementDraft:
    title: str
    bullets: tuple[str, ...]
    description: str


def create_advertisement_draft(
    name: str,
    attributes: Mapping[str, str],
    *,
    marketplace: str,
) -> AdvertisementDraft:
    """Cria copy apenas com fatos fornecidos, sem completar lacunas por suposição."""

    clean_name = name.strip()
    normalized_marketplace = marketplace.strip().lower().replace(" ", "_")
    if not clean_name:
        raise ValueError("O produto precisa de um nome.")
    if normalized_marketplace not in SUPPORTED_MARKETPLACES:
        raise ValueError("Marketplace suportado: shopee ou mercado_livre.")

    facts = tuple(
        (str(key).strip(), str(value).strip())
        for key, value in attributes.items()
        if str(key).strip() and str(value).strip()
    )
    bullets = tuple(f"{key}: {value}" for key, value in facts)
    title_suffix = " ".join(value for _, value in facts[:2])
    title = f"{clean_name} {title_suffix}".strip()
    description = (
        f"{clean_name}. " + " | ".join(bullets)
        if bullets
        else f"{clean_name}. Confirme os atributos antes de publicar."
    )
    return AdvertisementDraft(title=title[:60], bullets=bullets, description=description)


def analyze_batch(products: Iterable[ProductInput]) -> list[ProfitAnalysis]:
    """Analisa uma fila preservando a ordem de entrada."""

    return [analyze_profit(product) for product in products]


__all__ = [
    "AdvertisementDraft",
    "PotentialAnalysis",
    "PotentialSignals",
    "ProductInput",
    "ProfitAnalysis",
    "SUPPORTED_MARKETPLACES",
    "analyze_batch",
    "analyze_potential",
    "analyze_profit",
    "create_advertisement_draft",
]
