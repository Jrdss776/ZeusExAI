"""Testes do modo de precificação manual, sem API."""

from decimal import Decimal

import pytest

from openjarvis.zeusex.marketplace_pricing import (
    ManualProduct,
    MarketplaceFees,
    calculate_batch,
    calculate_pricing,
    compare_marketplaces,
)


def _product(**overrides) -> ManualProduct:
    values = {
        "sku": "SKU-001",
        "name": "Areia biodegradável",
        "product_cost": "50",
        "packaging_cost": "3",
        "operational_cost": "2",
        "desired_margin_percent": "20",
        "promotional_margin_percent": "10",
        "current_price": "100",
    }
    values.update(overrides)
    return ManualProduct(**values)


def _fees(marketplace="mercado_livre", **overrides) -> MarketplaceFees:
    values = {
        "marketplace": marketplace,
        "commission_percent": "12",
        "payment_fee_percent": "2",
        "tax_percent": "4",
        "advertising_percent": "2",
        "fixed_fee": "3",
        "shipping_cost": "7",
    }
    values.update(overrides)
    return MarketplaceFees(**values)


def test_calculates_minimum_recommended_and_promotional_prices() -> None:
    result = calculate_pricing(_product(), _fees())

    assert result.minimum_price == Decimal("81.25")
    assert result.promotional_price == Decimal("92.86")
    assert result.recommended_price == Decimal("108.34")


def test_calculates_real_profit_and_margin_at_current_price() -> None:
    result = calculate_pricing(_product(), _fees())

    assert result.current_profit == Decimal("15.00")
    assert result.current_margin_percent == Decimal("15.00")
    assert result.alert == "abaixo_recomendado"


def test_alerts_when_current_price_is_below_minimum() -> None:
    result = calculate_pricing(_product(current_price="80"), _fees())

    assert result.current_profit == Decimal("-1.00")
    assert result.alert == "abaixo_minimo"


def test_marks_product_without_current_price() -> None:
    result = calculate_pricing(_product(current_price=None), _fees())

    assert result.current_profit is None
    assert result.current_margin_percent is None
    assert result.alert == "sem_preco"


def test_rounds_target_price_up_to_protect_margin() -> None:
    result = calculate_pricing(
        _product(product_cost="10", packaging_cost="0", operational_cost="0"),
        _fees(commission_percent="0", payment_fee_percent="0", tax_percent="0", advertising_percent="0", fixed_fee="0", shipping_cost="0"),
    )

    assert result.recommended_price == Decimal("12.50")


def test_rejects_impossible_combination_of_fees_and_margin() -> None:
    with pytest.raises(ValueError, match="inviável"):
        calculate_pricing(
            _product(desired_margin_percent="40"),
            _fees(commission_percent="40", payment_fee_percent="10", tax_percent="10", advertising_percent="0"),
        )


def test_rejects_promotional_margin_above_desired_margin() -> None:
    with pytest.raises(ValueError, match="promocional"):
        _product(desired_margin_percent="10", promotional_margin_percent="15")


def test_comparison_identifies_marketplace_with_lower_recommended_price() -> None:
    comparison = compare_marketplaces(
        _product(),
        _fees("mercado_livre"),
        _fees("shopee", commission_percent="8"),
    )

    assert comparison.lowest_recommended_marketplace == "shopee"
    assert comparison.recommended_difference == Decimal("6.77")


def test_batch_preserves_order_and_accepts_up_to_limit() -> None:
    products = [_product(sku="A"), _product(sku="B", name="Produto B")]
    results = calculate_batch(products, _fees(), _fees("shopee"))

    assert [result.sku for result in results] == ["A", "B"]


def test_batch_rejects_duplicate_skus() -> None:
    with pytest.raises(ValueError, match="duplicado"):
        calculate_batch(
            [_product(sku="A"), _product(sku="a")],
            _fees(),
            _fees("shopee"),
        )


def test_batch_rejects_more_than_configured_limit() -> None:
    with pytest.raises(ValueError, match="no máximo 1"):
        calculate_batch(
            [_product(sku="A"), _product(sku="B")],
            _fees(),
            _fees("shopee"),
            maximum_products=1,
        )


def test_rejects_negative_costs_and_invalid_marketplace() -> None:
    with pytest.raises(ValueError, match="não pode ser negativo"):
        _product(packaging_cost="-1")
    with pytest.raises(ValueError, match="Marketplace suportado"):
        _fees("amazon")
