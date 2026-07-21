"""Testes do modo Achadinhos do JR e campanhas."""

import json

import pytest

from openjarvis.zeusex.campaigns import (
    ACHADINHOS_JR_TEMPLATE,
    CatalogItem,
    campaign_from_mapping,
    suggest_combinations,
)


def _payload():
    return {
        "product": {
            "name": "Areia biodegradável",
            "marketplace": "shopee",
            "sale_price": "49.90",
            "product_cost": "25",
        },
        "attributes": {
            "Material": "mandioca",
            "Peso": "4 kg",
        },
    }


def test_achadinhos_jr_generates_branded_campaign() -> None:
    campaign = campaign_from_mapping(_payload())
    decoded = json.loads(campaign.to_json())

    assert campaign.template == ACHADINHOS_JR_TEMPLATE
    assert decoded["template"]["brand"] == "Achadinhos do JR"
    assert "Material: mandioca" in campaign.to_json()
    assert "garantia" not in campaign.to_json().lower()


def test_kit_requires_explicit_group() -> None:
    suggestions = suggest_combinations(
        [
            CatalogItem("Produto A", kit_group="higiene"),
            CatalogItem("Produto B", kit_group="higiene"),
            CatalogItem("Sem relação"),
        ]
    )

    kits = [item for item in suggestions if item.kind == "kit"]
    assert len(kits) == 1
    assert kits[0].suggested == ("Produto B",)


def test_upsell_requires_same_category_and_higher_supplied_price() -> None:
    suggestions = suggest_combinations(
        [
            CatalogItem("Básico", category="areia", price="30"),
            CatalogItem("Premium", category="areia", price="50"),
            CatalogItem("Outro", category="ração", price="100"),
        ]
    )

    upsells = [item for item in suggestions if item.kind == "upsell"]
    assert len(upsells) == 1
    assert upsells[0].primary == "Básico"
    assert upsells[0].suggested == ("Premium",)


def test_cross_sell_requires_named_complement() -> None:
    suggestions = suggest_combinations(
        [
            CatalogItem("Areia", complements=("Pá coletora", "Inexistente")),
            CatalogItem("Pá coletora"),
        ]
    )

    cross_sell = [item for item in suggestions if item.kind == "cross_sell"]
    assert len(cross_sell) == 1
    assert cross_sell[0].suggested == ("Pá coletora",)


def test_no_relationships_produce_no_suggestions() -> None:
    assert suggest_combinations([CatalogItem("A"), CatalogItem("B")]) == ()


def test_duplicate_catalog_names_are_rejected() -> None:
    with pytest.raises(ValueError, match="únicos"):
        suggest_combinations([CatalogItem("A"), CatalogItem("A")])
