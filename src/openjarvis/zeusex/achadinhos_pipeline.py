"""Seleção auditável de oportunidades para campanhas Achadinhos do JR."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Mapping, Sequence
import json

from openjarvis.zeusex.campaigns import (
    ACHADINHOS_JR_TEMPLATE,
    CampaignPackage,
    CampaignTemplate,
    CatalogItem,
    generate_campaign,
)
from openjarvis.zeusex.commercial_batch import CommercialBatchResult
from openjarvis.zeusex.commercial_opportunities import (
    OpportunityAssessment,
    rank_opportunities,
)

_ALLOWED_CLASSIFICATIONS = frozenset({"alto", "moderado", "baixo"})


@dataclass(frozen=True, slots=True)
class AchadinhosSelectionPolicy:
    """Critérios explícitos para permitir a criação automática de campanhas."""

    minimum_score: Decimal = Decimal("50")
    allowed_classifications: frozenset[str] = frozenset({"alto", "moderado"})
    maximum_items: int | None = None
    target_margin_percent: Decimal = Decimal("20")

    def __post_init__(self) -> None:
        minimum_score = Decimal(str(self.minimum_score))
        target_margin = Decimal(str(self.target_margin_percent))
        allowed = frozenset(str(item).strip().lower() for item in self.allowed_classifications)

        if not Decimal("0") <= minimum_score <= Decimal("100"):
            raise ValueError("minimum_score precisa estar entre 0 e 100.")
        if not Decimal("0") <= target_margin < Decimal("100"):
            raise ValueError("target_margin_percent precisa estar entre 0 e 100.")
        if not allowed:
            raise ValueError("allowed_classifications não pode ficar vazio.")
        unknown = allowed - _ALLOWED_CLASSIFICATIONS
        if unknown:
            raise ValueError(
                "Classificações permitidas para campanha: alto, moderado ou baixo."
            )
        if self.maximum_items is not None and self.maximum_items <= 0:
            raise ValueError("maximum_items precisa ser maior que zero.")

        object.__setattr__(self, "minimum_score", minimum_score)
        object.__setattr__(self, "target_margin_percent", target_margin)
        object.__setattr__(self, "allowed_classifications", allowed)


@dataclass(frozen=True, slots=True)
class AchadinhosCampaignItem:
    """Campanha vinculada à avaliação que autorizou sua geração."""

    opportunity: OpportunityAssessment
    campaign: CampaignPackage


@dataclass(frozen=True, slots=True)
class AchadinhosCampaignBatch:
    """Resultado completo da seleção, incluindo itens rejeitados."""

    selected: tuple[AchadinhosCampaignItem, ...]
    rejected: tuple[OpportunityAssessment, ...]
    policy: AchadinhosSelectionPolicy

    @property
    def selected_count(self) -> int:
        return len(self.selected)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected)

    def to_dict(self) -> dict[str, Any]:
        def safe(value: object) -> Any:
            if isinstance(value, Decimal):
                return str(value)
            if isinstance(value, Mapping):
                return {str(key): safe(item) for key, item in value.items()}
            if isinstance(value, (list, tuple, frozenset, set)):
                return [safe(item) for item in value]
            return value

        return safe(asdict(self))

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )


def build_achadinhos_campaigns(
    batch: CommercialBatchResult,
    *,
    policy: AchadinhosSelectionPolicy = AchadinhosSelectionPolicy(),
    template: CampaignTemplate = ACHADINHOS_JR_TEMPLATE,
    catalog_by_listing: Mapping[str, Sequence[CatalogItem]] | None = None,
) -> AchadinhosCampaignBatch:
    """Seleciona oportunidades e gera campanhas sem promover itens não aprovados."""

    catalog = catalog_by_listing or {}
    analysis_by_id = {item.listing.listing_id: item for item in batch.analyses}
    if len(analysis_by_id) != len(batch.analyses):
        raise ValueError("Os identificadores dos anúncios analisados precisam ser únicos.")

    ranked = rank_opportunities(
        batch.analyses,
        target_margin_percent=policy.target_margin_percent,
    )
    selected: list[AchadinhosCampaignItem] = []
    rejected: list[OpportunityAssessment] = []

    for opportunity in ranked:
        approved = (
            opportunity.classification in policy.allowed_classifications
            and opportunity.score >= policy.minimum_score
        )
        if approved and (
            policy.maximum_items is None or len(selected) < policy.maximum_items
        ):
            result = analysis_by_id[opportunity.listing_id]
            selected.append(
                AchadinhosCampaignItem(
                    opportunity=opportunity,
                    campaign=generate_campaign(
                        result.report,
                        template=template,
                        catalog=tuple(catalog.get(opportunity.listing_id, ())),
                    ),
                )
            )
        else:
            rejected.append(opportunity)

    return AchadinhosCampaignBatch(
        selected=tuple(selected),
        rejected=tuple(rejected),
        policy=policy,
    )


__all__ = [
    "AchadinhosCampaignBatch",
    "AchadinhosCampaignItem",
    "AchadinhosSelectionPolicy",
    "build_achadinhos_campaigns",
]
