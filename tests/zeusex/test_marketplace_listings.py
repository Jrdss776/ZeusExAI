"""Testes dos adaptadores e da comparação de concorrentes."""

from decimal import Decimal

import pytest

from openjarvis.zeusex.competitors import compare_listings
from openjarvis.zeusex.marketplace_listings import MercadoLivreAdapter, ShopeeAdapter


def test_shopee_adapter_preserves_unknown_metrics_as_none() -> None:
    listing = ShopeeAdapter().normalize(
        {"item_id": 10, "name": "Areia vegetal", "price": "39.90"}
    )

    assert listing.marketplace == "shopee"
    assert listing.price == Decimal("39.90")
    assert listing.sold_count is None
    assert listing.rating is None


def test_mercado_livre_adapter_maps_public_fields() -> None:
    listing = MercadoLivreAdapter().normalize(
        {
            "id": "MLB123",
            "title": "Areia biodegradável",
            "price": 45.5,
            "permalink": "https://produto.example",
            "sold_quantity": 12,
            "seller": {"nickname": "LOJA"},
        }
    )

    assert listing.listing_id == "MLB123"
    assert listing.seller == "LOJA"
    assert listing.sold_count == 12


def test_adapter_rejects_missing_required_fact() -> None:
    with pytest.raises(ValueError, match="price"):
        ShopeeAdapter().normalize({"item_id": 10, "name": "Produto"})


def test_comparison_uses_only_known_sales() -> None:
    adapter = ShopeeAdapter()
    items = [
        adapter.normalize({"item_id": 1, "name": "A", "price": "30", "sold": 5}),
        adapter.normalize({"item_id": 2, "name": "B", "price": "50", "sold": 20}),
        adapter.normalize({"item_id": 3, "name": "C", "price": "40"}),
    ]

    result = compare_listings(items)

    assert result.minimum_price == Decimal("30.00")
    assert result.maximum_price == Decimal("50.00")
    assert result.average_price == Decimal("40.00")
    assert result.median_price == Decimal("40.00")
    assert result.known_sales_total == 25
    assert result.best_selling_listing_id == "2"


def test_comparison_rejects_mixed_marketplaces() -> None:
    shopee = ShopeeAdapter().normalize({"item_id": 1, "name": "A", "price": "30"})
    ml = MercadoLivreAdapter().normalize({"id": "MLB1", "title": "B", "price": "30"})

    with pytest.raises(ValueError, match="único marketplace"):
        compare_listings([shopee, ml])
