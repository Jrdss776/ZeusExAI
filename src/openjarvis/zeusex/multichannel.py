"""Geração multicanal baseada somente em fatos validados da Análise 360."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import json
import re
import unicodedata

from openjarvis.zeusex.analysis_360 import Analysis360Report


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "", ascii_value.lower())


def _facts(report: Analysis360Report) -> tuple[str, ...]:
    return report.advertisement.bullets


def _description(name: str, facts: tuple[str, ...], price: str | None) -> str:
    lines = [name]
    lines.extend(f"- {fact}" for fact in facts)
    if price is not None:
        lines.append(f"- Preço informado: R$ {price}")
    lines.append("Confira as informações e condições no anúncio antes da compra.")
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class MarketplaceCopy:
    title: str
    bullets: tuple[str, ...]
    description: str


@dataclass(frozen=True, slots=True)
class SocialCopy:
    text: str
    hashtags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VideoScene:
    label: str
    narration: str
    on_screen_text: str


@dataclass(frozen=True, slots=True)
class VideoScript:
    duration_seconds: int
    scenes: tuple[VideoScene, ...]


@dataclass(frozen=True, slots=True)
class MultichannelPackage:
    shopee: MarketplaceCopy
    mercado_livre: MarketplaceCopy
    whatsapp: SocialCopy
    instagram: SocialCopy
    videos: tuple[VideoScript, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def to_markdown(self) -> str:
        lines = [
            "# Pacote multicanal",
            "",
            "## Shopee",
            "",
            f"**Título:** {self.shopee.title}",
            "",
            self.shopee.description,
            "",
            "## Mercado Livre",
            "",
            f"**Título:** {self.mercado_livre.title}",
            "",
            self.mercado_livre.description,
            "",
            "## WhatsApp",
            "",
            self.whatsapp.text,
            "",
            "## Instagram",
            "",
            self.instagram.text,
            "",
            " ".join(self.instagram.hashtags),
        ]
        for video in self.videos:
            lines.extend(
                [
                    "",
                    f"## Roteiro de {video.duration_seconds} segundos",
                    "",
                ]
            )
            for scene in video.scenes:
                lines.extend(
                    [
                        f"### {scene.label}",
                        f"- Narração: {scene.narration}",
                        f"- Texto na tela: {scene.on_screen_text}",
                    ]
                )
        return "\n".join(lines).rstrip() + "\n"


def _video_scripts(
    name: str,
    facts: tuple[str, ...],
    price: str | None,
) -> tuple[VideoScript, ...]:
    primary_fact = facts[0] if facts else "Confira os dados confirmados do produto."
    secondary_facts = " | ".join(facts[1:3]) if len(facts) > 1 else primary_fact
    price_text = f"Preço informado: R$ {price}" if price is not None else "Consulte o anúncio."
    closing = "Confira todas as informações no anúncio."

    short = VideoScript(
        15,
        (
            VideoScene("Abertura", f"Conheça {name}.", name),
            VideoScene("Destaque", primary_fact, primary_fact),
            VideoScene("Encerramento", closing, price_text),
        ),
    )
    medium = VideoScript(
        30,
        (
            VideoScene("Abertura", f"Você está procurando informações sobre {name}?", name),
            VideoScene("Fato principal", primary_fact, primary_fact),
            VideoScene("Outros dados", secondary_facts, secondary_facts),
            VideoScene("Preço", price_text, price_text),
            VideoScene("Encerramento", closing, "Confira no anúncio"),
        ),
    )
    long = VideoScript(
        60,
        (
            VideoScene("Abertura", f"Veja os detalhes confirmados de {name}.", name),
            VideoScene("Apresentação", primary_fact, primary_fact),
            VideoScene("Características", secondary_facts, secondary_facts),
            VideoScene(
                "Transparência",
                "Use somente as características exibidas e confirme os demais dados no anúncio.",
                "Informações verificáveis",
            ),
            VideoScene("Preço", price_text, price_text),
            VideoScene("Encerramento", closing, "Confira todos os detalhes"),
        ),
    )
    return short, medium, long


def generate_multichannel_content(
    report: Analysis360Report,
    *,
    include_price: bool = True,
) -> MultichannelPackage:
    """Adapta fatos do relatório sem criar novos atributos ou promessas."""

    product = report.profit.product
    facts = _facts(report)
    price = str(report.profit.revenue) if include_price else None
    description = _description(product.name, facts, price)
    title = report.advertisement.title

    marketplace_bullets = facts + ((f"Preço informado: R$ {price}",) if price is not None else ())
    shopee = MarketplaceCopy(title=title, bullets=marketplace_bullets, description=description)
    mercado_livre = MarketplaceCopy(
        title=title,
        bullets=marketplace_bullets,
        description=description,
    )

    fact_text = " | ".join(facts) if facts else "Confira os dados no anúncio."
    price_text = f" Preço informado: R$ {price}." if price is not None else ""
    whatsapp = SocialCopy(
        text=f"{product.name}. {fact_text}.{price_text} Confira todos os detalhes no anúncio."
    )

    hashtag_candidates = (
        _slug(product.name),
        _slug(product.marketplace),
        "zeusexai",
    )
    hashtags = tuple(f"#{item}" for item in dict.fromkeys(hashtag_candidates) if item)
    instagram = SocialCopy(
        text=f"{product.name}\n\n{fact_text}.{price_text}\n\nConfira os detalhes no anúncio.",
        hashtags=hashtags,
    )
    return MultichannelPackage(
        shopee=shopee,
        mercado_livre=mercado_livre,
        whatsapp=whatsapp,
        instagram=instagram,
        videos=_video_scripts(product.name, facts, price),
    )


__all__ = [
    "MarketplaceCopy",
    "MultichannelPackage",
    "SocialCopy",
    "VideoScene",
    "VideoScript",
    "generate_multichannel_content",
]
