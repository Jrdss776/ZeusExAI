"""Testes da geração de conteúdo multicanal."""

import json

from openjarvis.zeusex.analysis_360 import build_analysis_360
from openjarvis.zeusex.marketplace import ProductInput
from openjarvis.zeusex.multichannel import generate_multichannel_content


def _report():
    return build_analysis_360(
        ProductInput(
            name="Areia biodegradável",
            marketplace="shopee",
            sale_price="49.90",
            product_cost="25",
        ),
        attributes={
            "Material": "mandioca",
            "Peso": "4 kg",
        },
    )


def test_multichannel_uses_only_validated_facts() -> None:
    package = generate_multichannel_content(_report())

    rendered = package.to_json()
    assert "Material: mandioca" in rendered
    assert "Peso: 4 kg" in rendered
    assert "49.90" in rendered
    assert "garantia" not in rendered.lower()
    assert "frete grátis" not in rendered.lower()


def test_package_contains_all_channels_and_video_lengths() -> None:
    package = generate_multichannel_content(_report())

    assert package.shopee.title
    assert package.mercado_livre.title
    assert package.whatsapp.text
    assert package.instagram.hashtags
    assert [video.duration_seconds for video in package.videos] == [15, 30, 60]


def test_can_omit_price_from_every_channel() -> None:
    package = generate_multichannel_content(_report(), include_price=False)

    assert "49.90" not in package.to_json()
    assert "Preço informado" not in package.to_json()


def test_json_and_markdown_exports_are_valid() -> None:
    package = generate_multichannel_content(_report())
    decoded = json.loads(package.to_json())
    markdown = package.to_markdown()

    assert decoded["videos"][0]["duration_seconds"] == 15
    assert "## Shopee" in markdown
    assert "## Roteiro de 60 segundos" in markdown


def test_hashtags_are_normalized_without_accents_or_spaces() -> None:
    package = generate_multichannel_content(_report())

    assert "#areiabiodegradavel" in package.instagram.hashtags
    assert all(" " not in hashtag for hashtag in package.instagram.hashtags)
