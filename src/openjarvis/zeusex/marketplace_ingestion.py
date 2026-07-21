"""Ingestão segura de respostas de marketplaces antes da análise comercial."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from openjarvis.zeusex.marketplace_listings import (
    MarketplaceAdapter,
    MercadoLivreAdapter,
    NormalizedListing,
    ShopeeAdapter,
)


@dataclass(frozen=True, slots=True)
class IngestionBatch:
    """Lote normalizado com rastreabilidade do formato recebido."""

    marketplace: str
    listings: tuple[NormalizedListing, ...]
    envelope: str

    @property
    def count(self) -> int:
        return len(self.listings)


class MarketplaceIngestionService:
    """Converte envelopes conhecidos em anúncios normalizados, sem rede ou escrita."""

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

    @staticmethod
    def _as_records(value: object, *, envelope: str) -> tuple[Mapping[str, Any], ...]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise ValueError(f"Envelope inválido: {envelope} precisa conter uma lista.")

        records: list[Mapping[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                raise ValueError(
                    f"Registro inválido no envelope {envelope}, posição {index}."
                )
            records.append(item)
        return tuple(records)

    @staticmethod
    def _extract_shopee(payload: Mapping[str, Any]) -> tuple[tuple[Mapping[str, Any], ...], str]:
        if all(key in payload for key in ("item_id", "name", "price")):
            return (payload,), "single"
        if "items" in payload:
            return MarketplaceIngestionService._as_records(
                payload["items"], envelope="items"
            ), "items"
        data = payload.get("data")
        if isinstance(data, Mapping) and "items" in data:
            return MarketplaceIngestionService._as_records(
                data["items"], envelope="data.items"
            ), "data.items"
        raise ValueError(
            "Resposta Shopee não reconhecida: esperado anúncio, items ou data.items."
        )

    @staticmethod
    def _extract_mercado_livre(
        payload: Mapping[str, Any],
    ) -> tuple[tuple[Mapping[str, Any], ...], str]:
        if all(key in payload for key in ("id", "title", "price")):
            return (payload,), "single"
        if "results" in payload:
            return MarketplaceIngestionService._as_records(
                payload["results"], envelope="results"
            ), "results"
        if "items" in payload:
            return MarketplaceIngestionService._as_records(
                payload["items"], envelope="items"
            ), "items"
        raise ValueError(
            "Resposta Mercado Livre não reconhecida: esperado anúncio, results ou items."
        )

    def ingest(self, marketplace: str, payload: Mapping[str, Any]) -> IngestionBatch:
        """Normaliza um anúncio ou lote e falha com contexto no primeiro item inválido."""

        normalized_marketplace = self._normalize_marketplace(marketplace)
        adapter = self._adapters.get(normalized_marketplace)
        if adapter is None:
            raise ValueError("Marketplace suportado: shopee ou mercado_livre.")
        if not isinstance(payload, Mapping):
            raise ValueError("A resposta do marketplace precisa ser um objeto.")

        if normalized_marketplace == "shopee":
            records, envelope = self._extract_shopee(payload)
        elif normalized_marketplace == "mercado_livre":
            records, envelope = self._extract_mercado_livre(payload)
        else:
            raise ValueError(
                "O adaptador personalizado precisa declarar um extrator de envelope."
            )

        listings: list[NormalizedListing] = []
        for index, record in enumerate(records):
            try:
                listings.append(adapter.normalize(record))
            except ValueError as exc:
                raise ValueError(
                    f"Anúncio inválido no envelope {envelope}, posição {index}: {exc}"
                ) from exc

        return IngestionBatch(
            marketplace=normalized_marketplace,
            listings=tuple(listings),
            envelope=envelope,
        )


__all__ = ["IngestionBatch", "MarketplaceIngestionService"]
