"""Precificação manual e determinística para marketplaces.

O módulo não acessa contas externas nem altera anúncios. As entradas podem vir
da interface manual, de arquivos ou, futuramente, de adaptadores de API.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from typing import Iterable

SUPPORTED_MARKETPLACES = ("mercado_livre", "shopee")
MONEY = Decimal("0.01")
PERCENT = Decimal("0.01")
HUNDRED = Decimal("100")


def _decimal(value: Decimal | int | float | str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"Valor numérico inválido: {value!r}.") from exc
    if not result.is_finite():
        raise ValueError("Valores financeiros precisam ser finitos.")
    return result


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _price(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_CEILING)


def _percent(value: Decimal) -> Decimal:
    return value.quantize(PERCENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class MarketplaceFees:
    """Taxas editáveis de um canal, sem valores presumidos."""

    marketplace: str
    commission_percent: Decimal = Decimal("0")
    payment_fee_percent: Decimal = Decimal("0")
    tax_percent: Decimal = Decimal("0")
    advertising_percent: Decimal = Decimal("0")
    fixed_fee: Decimal = Decimal("0")
    shipping_cost: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        marketplace = self.marketplace.strip().lower().replace(" ", "_")
        if marketplace not in SUPPORTED_MARKETPLACES:
            raise ValueError("Marketplace suportado: mercado_livre ou shopee.")
        object.__setattr__(self, "marketplace", marketplace)
        for name in (
            "commission_percent",
            "payment_fee_percent",
            "tax_percent",
            "advertising_percent",
            "fixed_fee",
            "shipping_cost",
        ):
            value = _decimal(getattr(self, name))
            if value < 0:
                raise ValueError(f"{name} não pode ser negativo.")
            object.__setattr__(self, name, value)
        if self.variable_percent >= HUNDRED:
            raise ValueError("A soma das taxas percentuais precisa ser menor que 100%.")

    @property
    def variable_percent(self) -> Decimal:
        return (
            self.commission_percent
            + self.payment_fee_percent
            + self.tax_percent
            + self.advertising_percent
        )


@dataclass(frozen=True, slots=True)
class ManualProduct:
    """Produto cadastrado manualmente ou importado de planilha."""

    sku: str
    name: str
    product_cost: Decimal
    packaging_cost: Decimal = Decimal("0")
    operational_cost: Decimal = Decimal("0")
    desired_margin_percent: Decimal = Decimal("20")
    promotional_margin_percent: Decimal = Decimal("10")
    current_price: Decimal | None = None

    def __post_init__(self) -> None:
        sku = self.sku.strip()
        name = self.name.strip()
        if not sku:
            raise ValueError("O produto precisa de um SKU.")
        if not name:
            raise ValueError("O produto precisa de um nome.")
        object.__setattr__(self, "sku", sku)
        object.__setattr__(self, "name", name)
        for field_name in (
            "product_cost",
            "packaging_cost",
            "operational_cost",
            "desired_margin_percent",
            "promotional_margin_percent",
        ):
            value = _decimal(getattr(self, field_name))
            if value < 0:
                raise ValueError(f"{field_name} não pode ser negativo.")
            object.__setattr__(self, field_name, value)
        if self.current_price is not None:
            current_price = _decimal(self.current_price)
            if current_price < 0:
                raise ValueError("current_price não pode ser negativo.")
            object.__setattr__(self, "current_price", current_price)
        if self.product_cost <= 0:
            raise ValueError("O custo do produto precisa ser maior que zero.")
        if self.desired_margin_percent >= HUNDRED:
            raise ValueError("A margem desejada precisa ser menor que 100%.")
        if self.promotional_margin_percent > self.desired_margin_percent:
            raise ValueError("A margem promocional não pode superar a margem desejada.")

    @property
    def base_cost(self) -> Decimal:
        return self.product_cost + self.packaging_cost + self.operational_cost


@dataclass(frozen=True, slots=True)
class PricingResult:
    product: ManualProduct
    fees: MarketplaceFees
    minimum_price: Decimal
    recommended_price: Decimal
    promotional_price: Decimal
    current_profit: Decimal | None
    current_margin_percent: Decimal | None
    alert: str

    @property
    def marketplace(self) -> str:
        return self.fees.marketplace


def _target_price(base_cost: Decimal, fixed_cost: Decimal, variable: Decimal, margin: Decimal) -> Decimal:
    denominator = Decimal("1") - variable / HUNDRED - margin / HUNDRED
    if denominator <= 0:
        raise ValueError("Taxas e margem deixam o preço matematicamente inviável.")
    return _price((base_cost + fixed_cost) / denominator)


def calculate_pricing(product: ManualProduct, fees: MarketplaceFees) -> PricingResult:
    """Calcula preços e saúde do preço atual para um marketplace."""

    variable = fees.variable_percent
    minimum = _target_price(product.base_cost, fees.fixed_fee + fees.shipping_cost, variable, Decimal("0"))
    recommended = _target_price(
        product.base_cost,
        fees.fixed_fee + fees.shipping_cost,
        variable,
        product.desired_margin_percent,
    )
    promotional = _target_price(
        product.base_cost,
        fees.fixed_fee + fees.shipping_cost,
        variable,
        product.promotional_margin_percent,
    )

    profit: Decimal | None = None
    real_margin: Decimal | None = None
    if product.current_price is None or product.current_price <= 0:
        alert = "sem_preco"
    else:
        current = product.current_price
        profit = current * (Decimal("1") - variable / HUNDRED) - (
            product.base_cost + fees.fixed_fee + fees.shipping_cost
        )
        real_margin = profit / current * HUNDRED
        if current < minimum:
            alert = "abaixo_minimo"
        elif real_margin < product.promotional_margin_percent:
            alert = "margem_critica"
        elif real_margin < product.desired_margin_percent:
            alert = "abaixo_recomendado"
        else:
            alert = "saudavel"

    return PricingResult(
        product=product,
        fees=fees,
        minimum_price=minimum,
        recommended_price=recommended,
        promotional_price=promotional,
        current_profit=_money(profit) if profit is not None else None,
        current_margin_percent=_percent(real_margin) if real_margin is not None else None,
        alert=alert,
    )


@dataclass(frozen=True, slots=True)
class MarketplaceComparison:
    sku: str
    mercado_livre: PricingResult
    shopee: PricingResult
    lowest_recommended_marketplace: str
    recommended_difference: Decimal


def compare_marketplaces(
    product: ManualProduct,
    mercado_livre_fees: MarketplaceFees,
    shopee_fees: MarketplaceFees,
) -> MarketplaceComparison:
    """Compara os dois canais sem fazer qualquer ação externa."""

    mercado_livre = calculate_pricing(product, mercado_livre_fees)
    shopee = calculate_pricing(product, shopee_fees)
    if mercado_livre.recommended_price <= shopee.recommended_price:
        lowest = "mercado_livre"
    else:
        lowest = "shopee"
    difference = abs(mercado_livre.recommended_price - shopee.recommended_price)
    return MarketplaceComparison(
        sku=product.sku,
        mercado_livre=mercado_livre,
        shopee=shopee,
        lowest_recommended_marketplace=lowest,
        recommended_difference=_money(difference),
    )


def calculate_batch(
    products: Iterable[ManualProduct],
    mercado_livre_fees: MarketplaceFees,
    shopee_fees: MarketplaceFees,
    *,
    maximum_products: int = 1000,
) -> list[MarketplaceComparison]:
    """Precifica até mil produtos, preservando a ordem da importação."""

    items = list(products)
    if len(items) > maximum_products:
        raise ValueError(f"O lote aceita no máximo {maximum_products} produtos.")
    seen: set[str] = set()
    for product in items:
        normalized = product.sku.casefold()
        if normalized in seen:
            raise ValueError(f"SKU duplicado no lote: {product.sku}.")
        seen.add(normalized)
    return [
        compare_marketplaces(product, mercado_livre_fees, shopee_fees)
        for product in items
    ]


__all__ = [
    "ManualProduct",
    "MarketplaceComparison",
    "MarketplaceFees",
    "PricingResult",
    "calculate_batch",
    "calculate_pricing",
    "compare_marketplaces",
]
