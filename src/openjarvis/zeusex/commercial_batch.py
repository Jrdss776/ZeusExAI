"""Orquestra ingestão e análise comercial determinística em lote."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from openjarvis.zeusex.commercial_analysis import (
    CommercialAnalysisResult,
    CommercialAnalysisService,
    CommercialCosts,
)
from openjarvis.zeusex.marketplace import PotentialSignals
from openjarvis.zeusex.marketplace_ingestion import (
    IngestionBatch,
    MarketplaceIngestionService,
)
from openjarvis.zeusex.marketplace_listings import NormalizedListing


@dataclass(frozen=True, slots=True)
class CommercialBatchRequest:
    """Entrada de lote com evidências associadas pelo identificador do anúncio."""

    marketplace: str
    payload: Mapping[str, Any]
    costs_by_listing: Mapping[str, CommercialCosts]
    default_costs: CommercialCosts | None = None
    attributes_by_listing: Mapping[str, Mapping[str, str]] | None = None
    signals_by_listing: Mapping[str, PotentialSignals] | None = None
    competitors_by_listing: Mapping[
        str,
        Sequence[NormalizedListing | Mapping[str, Any]],
    ] | None = None


@dataclass(frozen=True, slots=True)
class CommercialBatchResult:
    """Resultado auditável que preserva os metadados da ingestão."""

    ingestion: IngestionBatch
    analyses: tuple[CommercialAnalysisResult, ...]

    @property
    def count(self) -> int:
        return len(self.analyses)


class CommercialBatchService:
    """Liga envelopes externos ao motor comercial sem inventar custos ausentes."""

    def __init__(
        self,
        *,
        ingestion: MarketplaceIngestionService | None = None,
        analysis: CommercialAnalysisService | None = None,
    ) -> None:
        self._ingestion = ingestion or MarketplaceIngestionService()
        self._analysis = analysis or CommercialAnalysisService()

    def analyze(self, request: CommercialBatchRequest) -> CommercialBatchResult:
        ingestion = self._ingestion.ingest(request.marketplace, request.payload)
        attributes = request.attributes_by_listing or {}
        signals = request.signals_by_listing or {}
        competitors = request.competitors_by_listing or {}

        analyses: list[CommercialAnalysisResult] = []
        for listing in ingestion.listings:
            costs = request.costs_by_listing.get(listing.listing_id)
            if costs is None:
                costs = request.default_costs
            if costs is None:
                raise ValueError(
                    "Custos ausentes para o anúncio "
                    f"{listing.listing_id}; informe costs_by_listing ou default_costs."
                )

            analyses.append(
                self._analysis.analyze_normalized(
                    listing,
                    costs,
                    attributes=attributes.get(listing.listing_id),
                    signals=signals.get(listing.listing_id),
                    competitors=tuple(competitors.get(listing.listing_id, ())),
                )
            )

        return CommercialBatchResult(ingestion, tuple(analyses))


__all__ = [
    "CommercialBatchRequest",
    "CommercialBatchResult",
    "CommercialBatchService",
]
