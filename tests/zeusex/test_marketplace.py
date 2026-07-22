"""Testes da Fase 14 — inteligência comercial do ZeusEXai."""

from decimal import Decimal

import pytest

from openjarvis.zeusex.marketplace import (
    PotentialSignals,
    ProductInput,
    analyze_batch,
    analyze_potential,
    analyze_profit,
    create_advertisement_draft,
)


def _product(**overrides) -> ProductInput:
    values = {
        "name": "Areia biodegradável",
        "marketplace": "shopee",
        "sale_price": "100",
        "product_cost": "50",
        "marketplace_fee_percent": "10",
        "fixed_fee": "2",
        "shipping_cost": "8",
        "tax_percent": "5",
    }
    values.update(overrides)
    return ProductInput(**values)


def test_profit_analysis_uses_decimal_money() -> None:
    result = analyze_profit(_product())

    assert result.marketplace_fee == Decimal("10.00")
    assert result.taxes == Decimal("5.00")
    assert result.total_cost == Decimal("75.00")
    assert result.profit == Decimal("25.00")
    assert result.margin_percent == Decimal("25.00")
    assert result.break_even_price == Decimal("70.59")
    assert result.profitable is True


def test_rejects_unsupported_marketplace_and_invalid_rates() -> None:
    with pytest.raises(ValueError, match="Marketplace"):
        _product(marketplace="desconhecido")
    with pytest.raises(ValueError, match="menor que 100"):
        _product(marketplace_fee_percent="80", tax_percent="20")


def test_potential_score_uses_only_explicit_signals() -> None:
    result = analyze_potential(
        PotentialSignals(
            demand="90",
            competition="30",
            margin="80",
            listing_quality="70",
        )
    )

    assert result.score == Decimal("80.00")
    assert result.classification == "alto"


def test_potential_rejects_unbounded_signal() -> None:
    with pytest.raises(ValueError, match="entre 0 e 100"):
        PotentialSignals(demand="101", competition="10", margin="20", listing_quality="30")


def test_advertisement_contains_only_supplied_facts() -> None:
    draft = create_advertisement_draft(
        "Areia biodegradável",
        {"Material": "mandioca", "Peso": "4 kg", "Garantia": ""},
        marketplace="mercado livre",
    )

    assert draft.title == "Areia biodegradável mandioca 4 kg"
    assert draft.bullets == ("Material: mandioca", "Peso: 4 kg")
    assert "Garantia" not in draft.description


def test_batch_preserves_product_order() -> None:
    products = [_product(name="Produto A"), _product(name="Produto B", sale_price="120")]
    results = analyze_batch(products)

    assert [item.product.name for item in results] == ["Produto A", "Produto B"]
