"""Normalização segura de dados comerciais da Shopee e do Mercado Livre."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping, Protocol

from openjarvis.zeusex.marketplace import SUPPORTED_MARKETPLACES

MONEY = Decimal("0.01")


def _decimal(value: object, *, field: str) -> Decimal:
    try:
        return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)
    except Exception as exc:
        raise ValueError(f"Campo monetário inválido: {field}.") from exc


def _optional_decimal(value: object | None, *, field: str) -> Decimal | None:
    return None if value in {None, ""} else _decimal(value, field=field)


def _optional_int(value: object | None, *, field: str) -> int | None:
    if value in {None, ""}:
        return None
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Campo inteiro inválido: {field}.") from exc
    if result < 0:
        raise ValueError(f"{field} não pode ser negativo.")
    return result


@dataclass(frozen=True, slots=True)
class NormalizedListing:
    """Representação comum sem completar métricas ausentes."""

    marketplace: str
    listing_id: str
    title: str
    price: Decimal
    url: str = ""
    seller: str = ""
    sold_count: int | None = None
    rating: Decimal | None = None
    review_count: int | None = None

    def __post_init__(self) -> None:
        marketplace = self.marketplace.strip().lower().replace(" ", "_")
        listing_id = self.listing_id.strip()
        title = self.title.strip()
        if marketplace not in SUPPORTED_MARKETPLACES:
            raise ValueError("Marketplace suportado: shopee ou mercado_livre.")
        if not listing_id:
            raise ValueError("O anúncio precisa de um identificador.")
        if not title:
            raise ValueError("O anúncio precisa de um título.")

        price = _decimal(self.price, field="price")
        if price < 0:
            raise ValueError("price não pode ser negativo.")
        rating = _optional_decimal(self.rating, field="rating")
        if rating is not None and not Decimal("0") <= rating <= Decimal("5"):
            raise ValueError("rating precisa estar entre 0 e 5.")

        object.__setattr__(self, "marketplace", marketplace)
        object.__setattr__(self, "listing_id", listing_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "rating", rating)
        object.__setattr__(
            self,
            "sold_count",
            _optional_int(self.sold_count, field="sold_count"),
        )
        object.__setattr__(
            self,
            "review_count",
            _optional_int(self.review_count, field="review_count"),
        )


class MarketplaceAdapter(Protocol):
    """Contrato para futuras integrações HTTP autenticadas ou públicas."""

    marketplace: str

    def normalize(self, payload: Mapping[str, Any]) -> NormalizedListing:
        """Normaliza uma resposta externa sem executar publicação."""


def _required(payload: Mapping[str, Any], key: str) -> object:
    value = payload.get(key)
    if value in {None, ""}:
        raise ValueError(f"Campo obrigatório ausente: {key}.")
    return value


@dataclass(frozen=True, slots=True)
class ShopeeAdapter:
    marketplace: str = "shopee"

    def normalize(self, payload: Mapping[str, Any]) -> NormalizedListing:
        """Aceita o formato canônico produzido pela futura camada HTTP Shopee."""

        return NormalizedListing(
            marketplace=self.marketplace,
            listing_id=str(_required(payload, "item_id")),
            title=str(_required(payload, "name")),
            price=_decimal(_required(payload, "price"), field="price"),
            url=str(payload.get("url") or ""),
            seller=str(payload.get("shop_name") or ""),
            sold_count=_optional_int(payload.get("sold"), field="sold"),
            rating=_optional_decimal(payload.get("rating"), field="rating"),
            review_count=_optional_int(payload.get("review_count"), field="review_count"),
        )


@dataclass(frozen=True, slots=True)
class MercadoLivreAdapter:
    marketplace: str = "mercado_livre"

    def normalize(self, payload: Mapping[str, Any]) -> NormalizedListing:
        """Normaliza campos públicos usuais da API do Mercado Livre."""

        seller = payload.get("seller")
        seller_name = seller.get("nickname", "") if isinstance(seller, Mapping) else ""
        return NormalizedListing(
            marketplace=self.marketplace,
            listing_id=str(_required(payload, "id")),
            title=str(_required(payload, "title")),
            price=_decimal(_required(payload, "price"), field="price"),
            url=str(payload.get("permalink") or ""),
            seller=str(seller_name),
            sold_count=_optional_int(payload.get("sold_quantity"), field="sold_quantity"),
            rating=_optional_decimal(payload.get("rating_average"), field="rating_average"),
            review_count=_optional_int(payload.get("reviews_total"), field="reviews_total"),
        )


__all__ = [
    "MarketplaceAdapter",
    "MercadoLivreAdapter",
    "NormalizedListing",
    "ShopeeAdapter",
]
