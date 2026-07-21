"""Serviço unificado de análise comercial para marketplaces suportados."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence

from openjarvis.zeusex.analysis_360 import Analysis360Report, build_analysis_360
from openjarvis.zeusex.marketplace import PotentialSignals, ProductInput
from openjarvis.zeusex.marketplace_listings import (
    MarketplaceAdapter,
    MercadoLivreAdapter,
    NormalizedListing,
    ShopeeAdapter,
)


@dataclass(frozen=True, slots=True)
class CommercialCosts:
    """Custos explícitos usados para avaliar um anúncio normalizado."""

    product_cost: Decimal
    marketplace_fee_percent: Decimal = Decimal("0")
    fixed_fee: Decimal = Decimal("0")
    shipping_cost: Decimal = Decimal("0")
    tax_percent: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class CommercialAnalysisRequest:
    """Entrada independente do formato de resposta de cada marketplace."""

    marketplace: str
    listing: Mapping[str, Any]
    costs: CommercialCosts
    attributes: Mapping[str, str] | None = None
    signals: PotentialSignals | None = None
    competitors: Sequence[Mapping[str, Any]] = ()


@dataclass(frozen=True, slots=True)
class CommercialAnalysisResult:
    """Resultado com dados normalizados e relatório determinístico."""

    listing: NormalizedListing
    competitors: tuple[NormalizedListing, ...]
    report: Analysis360Report


class CommercialAnalysisService:
    """Normaliza Shopee/ML e reutiliza o motor comercial auditável."""

    def __init__(
        self,
        adapters: Mapping[str, MarketplaceAdapter] | None = None,
    ) -> None:
        configured = adapters or {
            "shopee": ShopeeAdapter(),
            "mercado_livre": MercadoLivreAdapter(),
        }
        self._adapters = {
            self._normalize_marketplace(name): adapter
            for name, adapter in configured.items()
        }

    @staticmethod
    def _normalize_marketplace(value: str) -> str:
        return value.strip().lower().replace(" ", "_")

    def analyze(self, request: CommercialAnalysisRequest) -> CommercialAnalysisResult:
        marketplace = self._normalize_marketplace(request.marketplace)
        adapter = self._adapters.get(marketplace)
        if adapter is None:
            raise ValueError("Marketplace suportado: shopee ou mercado_livre.")

        listing = adapter.normalize(request.listing)
        competitors = tuple(adapter.normalize(item) for item in request.competitors)
        costs = request.costs
        product = ProductInput(
            name=listing.title,
            marketplace=listing.marketplace,
            sale_price=listing.price,
            product_cost=costs.product_cost,
            marketplace_fee_percent=costs.marketplace_fee_percent,
            fixed_fee=costs.fixed_fee,
            shipping_cost=costs.shipping_cost,
            tax_percent=costs.tax_percent,
        )
        report = build_analysis_360(
            product,
            attributes=request.attributes,
            signals=request.signals,
            competitors=competitors,
        )
        return CommercialAnalysisResult(listing, competitors, report)


__all__ = [
    "CommercialAnalysisRequest",
    "CommercialAnalysisResult",
    "CommercialAnalysisService",
    "CommercialCosts",
]
