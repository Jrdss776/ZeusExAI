"""Campanhas reutilizáveis e modo Achadinhos do JR."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence
import json

from openjarvis.zeusex.analysis_360 import (
    Analysis360Report,
    analysis_360_from_mapping,
)
from openjarvis.zeusex.multichannel import (
    MultichannelPackage,
    generate_multichannel_content,
)


@dataclass(frozen=True, slots=True)
class CampaignTemplate:
    name: str
    brand: str
    call_to_action: str
    include_price: bool = True

    def __post_init__(self) -> None:
        for field_name in ("name", "brand", "call_to_action"):
            value = str(getattr(self, field_name)).strip()
            if not value:
                raise ValueError(f"{field_name} não pode ficar vazio.")
            object.__setattr__(self, field_name, value)


ACHADINHOS_JR_TEMPLATE = CampaignTemplate(
    name="achadinhos-jr",
    brand="Achadinhos do JR",
    call_to_action="Confira todos os detalhes no anúncio.",
    include_price=True,
)


@dataclass(frozen=True, slots=True)
class CatalogItem:
    name: str
    category: str = ""
    price: Decimal | None = None
    kit_group: str = ""
    complements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise ValueError("O item do catálogo precisa de um nome.")
        price = Decimal(str(self.price)) if self.price is not None else None
        if price is not None and price < 0:
            raise ValueError("O preço do item não pode ser negativo.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "category", self.category.strip())
        object.__setattr__(self, "price", price)
        object.__setattr__(self, "kit_group", self.kit_group.strip())
        object.__setattr__(
            self,
            "complements",
            tuple(item.strip() for item in self.complements if item.strip()),
        )


@dataclass(frozen=True, slots=True)
class CombinationSuggestion:
    kind: str
    primary: str
    suggested: tuple[str, ...]
    evidence: str


def suggest_combinations(
    catalog: Sequence[CatalogItem],
) -> tuple[CombinationSuggestion, ...]:
    """Usa somente relações explícitas e preços fornecidos."""

    items = list(catalog)
    names = {item.name for item in items}
    if len(names) != len(items):
        raise ValueError("Os nomes dos itens do catálogo precisam ser únicos.")

    suggestions: list[CombinationSuggestion] = []

    groups: dict[str, list[CatalogItem]] = {}
    for item in items:
        if item.kit_group:
            groups.setdefault(item.kit_group, []).append(item)
    for group_name, grouped in sorted(groups.items()):
        if len(grouped) >= 2:
            suggestions.append(
                CombinationSuggestion(
                    kind="kit",
                    primary=grouped[0].name,
                    suggested=tuple(item.name for item in grouped[1:]),
                    evidence=f"Grupo de kit informado: {group_name}.",
                )
            )

    categories: dict[str, list[CatalogItem]] = {}
    for item in items:
        if item.category and item.price is not None:
            categories.setdefault(item.category, []).append(item)
    for category, categorized in sorted(categories.items()):
        ordered = sorted(categorized, key=lambda item: (item.price, item.name))
        for current, upgrade in zip(ordered, ordered[1:]):
            if current.price is not None and upgrade.price is not None and upgrade.price > current.price:
                suggestions.append(
                    CombinationSuggestion(
                        kind="upsell",
                        primary=current.name,
                        suggested=(upgrade.name,),
                        evidence=(
                            f"Mesma categoria informada ({category}) e preço superior fornecido."
                        ),
                    )
                )

    seen_cross_sell: set[tuple[str, str]] = set()
    for item in items:
        for complement in item.complements:
            if complement not in names:
                continue
            key = tuple(sorted((item.name, complement)))
            if item.name == complement or key in seen_cross_sell:
                continue
            seen_cross_sell.add(key)
            suggestions.append(
                CombinationSuggestion(
                    kind="cross_sell",
                    primary=item.name,
                    suggested=(complement,),
                    evidence="Relação complementar informada pelo usuário.",
                )
            )

    return tuple(suggestions)


@dataclass(frozen=True, slots=True)
class CampaignPackage:
    template: CampaignTemplate
    content: MultichannelPackage
    combinations: tuple[CombinationSuggestion, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)

        def safe(item: object) -> Any:
            if isinstance(item, Decimal):
                return str(item)
            if isinstance(item, Mapping):
                return {str(key): safe(child) for key, child in item.items()}
            if isinstance(item, (list, tuple)):
                return [safe(child) for child in item]
            return item

        return safe(value)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def to_markdown(self) -> str:
        lines = [
            f"# Campanha — {self.template.brand}",
            "",
            f"- Modelo: {self.template.name}",
            f"- Chamada: {self.template.call_to_action}",
            "",
            self.content.to_markdown().rstrip(),
            "",
            "## Kits, upsell e cross-sell",
            "",
        ]
        if not self.combinations:
            lines.append("Nenhuma combinação foi criada sem relações explícitas.")
        else:
            for suggestion in self.combinations:
                suggested = ", ".join(suggestion.suggested)
                lines.append(
                    f"- **{suggestion.kind}**: {suggestion.primary} → {suggested}. "
                    f"{suggestion.evidence}"
                )
        return "\n".join(lines).rstrip() + "\n"


def generate_campaign(
    report: Analysis360Report,
    *,
    template: CampaignTemplate = ACHADINHOS_JR_TEMPLATE,
    catalog: Sequence[CatalogItem] = (),
) -> CampaignPackage:
    content = generate_multichannel_content(
        report,
        include_price=template.include_price,
    )
    return CampaignPackage(
        template=template,
        content=content,
        combinations=suggest_combinations(catalog),
    )


def campaign_from_mapping(
    payload: Mapping[str, Any],
    *,
    template: CampaignTemplate = ACHADINHOS_JR_TEMPLATE,
) -> CampaignPackage:
    report = analysis_360_from_mapping(payload)
    catalog_data = payload.get("catalog") or []
    if not isinstance(catalog_data, list):
        raise ValueError("Informe catalog como lista.")
    catalog = []
    for item in catalog_data:
        if not isinstance(item, Mapping):
            raise ValueError("Cada item do catálogo precisa ser um objeto.")
        normalized = dict(item)
        complements = normalized.get("complements") or ()
        if not isinstance(complements, (list, tuple)):
            raise ValueError("complements precisa ser uma lista.")
        normalized["complements"] = tuple(str(value) for value in complements)
        catalog.append(CatalogItem(**normalized))
    return generate_campaign(report, template=template, catalog=catalog)


__all__ = [
    "ACHADINHOS_JR_TEMPLATE",
    "CampaignPackage",
    "CampaignTemplate",
    "CatalogItem",
    "CombinationSuggestion",
    "campaign_from_mapping",
    "generate_campaign",
    "suggest_combinations",
]
