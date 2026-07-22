"""Testes da seleção de oportunidades para o modo Achadinhos do JR."""

from decimal import Decimal
import json

import pytest

from openjarvis.zeusex.achadinhos_pipeline import (
    AchadinhosSelectionPolicy,
    build_achadinhos_campaigns,
)
from openjarvis.zeusex.campaigns import CatalogItem
from openjarvis.zeusex.commercial_analysis import CommercialCosts
from openjarvis.zeusex.commercial_batch import (
    CommercialBatchRequest,
    CommercialBatchService,
)
from openjarvis.zeusex.marketplace import PotentialSignals
from openjarvis.zeusex.marketplace_listings import NormalizedListing


def _complete_batch():
    return CommercialBatchService().analyze(
        CommercialBatchRequest(
            marketplace="shopee",
            payload={
                "items": [
                    {"item_id": 10, "name": "Produto Forte", "price": "100"},
                    {"item_id": 20, "name": "Produto Inviável", "price": "40"},
                ]
            },
            costs_by_listing={
                "10": CommercialCosts(product_cost=Decimal("30")),
                "20": CommercialCosts(product_cost=Decimal("45")),
            },
            attributes_by_listing={
                "10": {"Material": "aço"},
                "20": {"Cor": "preta"},
            },
            signals_by_listing={
                "10": PotentialSignals("90", "10", "80", "90"),
                "20": PotentialSignals("40", "80", "10", "50"),
            },
            competitors_by_listing={
                "10": (
                    NormalizedListing("shopee", "C1", "Concorrente 1", "90"),
                    NormalizedListing("shopee", "C2", "Concorrente 2", "110"),
                ),
                "20": (
                    NormalizedListing("shopee", "C3", "Concorrente 3", "42"),
                ),
            },
        )
    )


def test_generates_campaign_only_for_approved_opportunity() -> None:
    result = build_achadinhos_campaigns(_complete_batch())

    assert result.selected_count == 1
    assert result.rejected_count == 1
    selected = result.selected[0]
    assert selected.opportunity.listing_id == "10"
    assert selected.opportunity.classification == "alto"
    assert selected.campaign.template.brand == "Achadinhos do JR"
    assert selected.campaign.content.whatsapp.text.startswith("Produto Forte")
    assert result.rejected[0].classification == "inviavel"


def test_keeps_catalog_relations_scoped_to_selected_listing() -> None:
    result = build_achadinhos_campaigns(
        _complete_batch(),
        catalog_by_listing={
            "10": (
                CatalogItem("Produto Forte", kit_group="kit-a"),
                CatalogItem("Acessório", kit_group="kit-a"),
            )
        },
    )

    combinations = result.selected[0].campaign.combinations
    assert len(combinations) == 1
    assert combinations[0].kind == "kit"
    assert combinations[0].suggested == ("Acessório",)


def test_rejects_profitable_listing_when_evidence_is_incomplete() -> None:
    batch = CommercialBatchService().analyze(
        CommercialBatchRequest(
            marketplace="mercado livre",
            payload={"id": "MLB1", "title": "Produto", "price": "100"},
            costs_by_listing={"MLB1": CommercialCosts(product_cost=Decimal("30"))},
        )
    )

    result = build_achadinhos_campaigns(batch)

    assert result.selected == ()
    assert result.rejected[0].classification == "dados_insuficientes"
    assert set(result.rejected[0].missing_evidence) == {
        "sinais_de_potencial",
        "concorrentes",
    }


def test_serializes_selection_with_auditable_policy() -> None:
    result = build_achadinhos_campaigns(
        _complete_batch(),
        policy=AchadinhosSelectionPolicy(
            minimum_score=Decimal("70"),
            maximum_items=1,
            target_margin_percent=Decimal("25"),
        ),
    )

    payload = json.loads(result.to_json())
    assert payload["policy"]["minimum_score"] == "70"
    assert payload["policy"]["target_margin_percent"] == "25"
    assert payload["selected"][0]["opportunity"]["listing_id"] == "10"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"minimum_score": Decimal("101")},
        {"maximum_items": 0},
        {"allowed_classifications": frozenset({"inviavel"})},
    ],
)
def test_rejects_unsafe_selection_policy(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        AchadinhosSelectionPolicy(**kwargs)
