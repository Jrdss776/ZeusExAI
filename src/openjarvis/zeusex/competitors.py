"""Comparação auditável de anúncios concorrentes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Iterable

from openjarvis.zeusex.marketplace_listings import NormalizedListing

MONEY = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CompetitorComparison:
    marketplace: str
    listing_count: int
    minimum_price: Decimal
    maximum_price: Decimal
    average_price: Decimal
    median_price: Decimal
    known_sales_total: int | None
    best_selling_listing_id: str | None


def compare_listings(listings: Iterable[NormalizedListing]) -> CompetitorComparison:
    """Compara apenas valores presentes e rejeita marketplaces misturados."""

    items = list(listings)
    if not items:
        raise ValueError("Informe ao menos um anúncio para comparação.")
    marketplaces = {item.marketplace for item in items}
    if len(marketplaces) != 1:
        raise ValueError("Compare anúncios de um único marketplace por vez.")

    prices = [item.price for item in items]
    average = sum(prices, Decimal("0")) / Decimal(len(prices))
    known_sales = [item for item in items if item.sold_count is not None]
    best = max(known_sales, key=lambda item: item.sold_count or 0) if known_sales else None

    return CompetitorComparison(
        marketplace=items[0].marketplace,
        listing_count=len(items),
        minimum_price=min(prices).quantize(MONEY, rounding=ROUND_HALF_UP),
        maximum_price=max(prices).quantize(MONEY, rounding=ROUND_HALF_UP),
        average_price=average.quantize(MONEY, rounding=ROUND_HALF_UP),
        median_price=Decimal(median(prices)).quantize(MONEY, rounding=ROUND_HALF_UP),
        known_sales_total=sum(item.sold_count or 0 for item in known_sales) if known_sales else None,
        best_selling_listing_id=best.listing_id if best else None,
    )


__all__ = ["CompetitorComparison", "compare_listings"]
