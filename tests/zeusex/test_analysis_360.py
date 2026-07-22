"""Testes do relatório comercial 360."""

from decimal import Decimal
import json

import pytest

from openjarvis.zeusex.analysis_360 import (
    analysis_360_from_mapping,
    build_analysis_360,
)
from openjarvis.zeusex.marketplace import PotentialSignals, ProductInput
from openjarvis.zeusex.marketplace_listings import NormalizedListing


def _product() -> ProductInput:
    return ProductInput(
        name="Areia biodegradável",
        marketplace="shopee",
        sale_price="50",
        product_cost="25",
        marketplace_fee_percent="10",
        fixed_fee="2",
        shipping_cost="3",
        tax_percent="5",
    )


def test_report_combines_all_commercial_sections() -> None:
    report = build_analysis_360(
        _product(),
        attributes={"Material": "mandioca", "Peso": "4 kg"},
        signals=PotentialSignals(
            demand="80",
            competition="30",
            margin="70",
            listing_quality="50",
        ),
        competitors=[
            NormalizedListing("shopee", "1", "Concorrente A", "45", sold_count=10),
            NormalizedListing("shopee", "2", "Concorrente B", "55"),
        ],
    )

    assert report.profit.profit == Decimal("12.50")
    assert report.potential is not None
    assert report.competitors is not None
    assert report.competitors.average_price == Decimal("50.00")
    assert report.advertisement.bullets == (
        "Material: mandioca",
        "Peso: 4 kg",
    )
    assert any("Melhorar título" in item for item in report.recommendations)


def test_json_export_keeps_decimal_values_exact() -> None:
    decoded = json.loads(build_analysis_360(_product()).to_json())

    assert decoded["profit"]["revenue"] == "50.00"
    assert decoded["profit"]["margin_percent"] == "25.00"


def test_markdown_marks_missing_inputs() -> None:
    markdown = build_analysis_360(_product()).to_markdown()

    assert "# Análise 360" in markdown
    assert "Sinais de potencial não informados." in markdown
    assert "Anúncios concorrentes não informados." in markdown


def test_mapping_parser_builds_complete_report() -> None:
    report = analysis_360_from_mapping(
        {
            "product": {
                "name": "Produto",
                "marketplace": "mercado_livre",
                "sale_price": "100",
                "product_cost": "40",
            },
            "attributes": {"Cor": "azul"},
            "signals": {
                "demand": "90",
                "competition": "20",
                "margin": "80",
                "listing_quality": "75",
            },
            "competitors": [
                {
                    "marketplace": "mercado_livre",
                    "listing_id": "MLB1",
                    "title": "Concorrente",
                    "price": "90",
                }
            ],
        }
    )

    assert report.potential is not None
    assert report.potential.classification == "alto"
    assert report.competitors is not None


def test_report_rejects_competitors_from_other_marketplace() -> None:
    competitor = NormalizedListing("mercado_livre", "MLB1", "Outro", "45")

    with pytest.raises(ValueError, match="mesmo marketplace"):
        build_analysis_360(_product(), competitors=[competitor])
