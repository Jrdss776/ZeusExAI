"""Orquestração auditável dos especialistas comerciais do ZeusExAI.

O módulo mantém fatos e criação separados: somente o coletor produz a ficha de
evidências; os demais especialistas recebem essa ficha imutável e precisam
referenciar suas fontes ao declarar fatos. Isso permite trocar modelos e
provedores sem relaxar a política de verificação.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import urlparse


class CommercialAction(str, Enum):
    ANALYSIS = "analysis"
    LISTING = "listing"
    VIDEO = "video"
    STRATEGY = "strategy"
    COMPLETE = "complete"


class SpecialistRole(str, Enum):
    PRODUCT_ANALYST = "product_analyst"
    COMPETITOR_ANALYST = "competitor_analyst"
    SALES_STRATEGIST = "sales_strategist"
    LISTING_WRITER = "listing_writer"
    VIDEO_WRITER = "video_writer"
    REVIEWER = "reviewer"


class PipelineStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    url: str
    title: str = ""
    retrieved_at: str = ""

    def __post_init__(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("A fonte precisa usar uma URL HTTP(S) válida.")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    field: str
    value: Any
    source_urls: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.field.strip():
            raise ValueError("O campo da evidência não pode ficar vazio.")
        if not self.source_urls:
            raise ValueError("Toda evidência precisa citar ao menos uma fonte.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "value": self.value,
            "source_urls": list(self.source_urls),
        }


@dataclass(frozen=True, slots=True)
class ProductEvidenceDossier:
    subject: str
    sources: tuple[EvidenceSource, ...]
    claims: tuple[EvidenceClaim, ...]
    missing_fields: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    collector_model: str = ""

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise ValueError("O produto ou link não pode ficar vazio.")
        source_urls = {source.url for source in self.sources}
        unknown = {
            url
            for claim in self.claims
            for url in claim.source_urls
            if url not in source_urls
        }
        if unknown:
            raise ValueError(
                "A ficha contém evidências ligadas a fontes não cadastradas: "
                + ", ".join(sorted(unknown))
            )

    @property
    def verified_fields(self) -> frozenset[str]:
        return frozenset(claim.field for claim in self.claims)

    @property
    def source_urls(self) -> frozenset[str]:
        return frozenset(source.url for source in self.sources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "sources": [source.to_dict() for source in self.sources],
            "claims": [claim.to_dict() for claim in self.claims],
            "missing_fields": list(self.missing_fields),
            "warnings": list(self.warnings),
            "collector_model": self.collector_model,
        }


@dataclass(frozen=True, slots=True)
class FactualAssertion:
    text: str
    source_urls: tuple[str, ...]
    claim_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("A afirmação factual não pode ficar vazia.")
        if not self.source_urls:
            raise ValueError("A afirmação factual precisa citar uma fonte.")
        if not self.claim_fields:
            raise ValueError("A afirmação factual precisa indicar os campos que a sustentam.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_urls": list(self.source_urls),
            "claim_fields": list(self.claim_fields),
        }


@dataclass(frozen=True, slots=True)
class SpecialistOutput:
    role: SpecialistRole
    content: str
    assertions: tuple[FactualAssertion, ...] = ()
    assumptions: tuple[str, ...] = ()
    missing_information: tuple[str, ...] = ()
    model: str = ""

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("O especialista não pode retornar conteúdo vazio.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "assertions": [item.to_dict() for item in self.assertions],
            "assumptions": list(self.assumptions),
            "missing_information": list(self.missing_information),
            "model": self.model,
        }


class EvidenceCollector(Protocol):
    def collect(self, subject: str) -> ProductEvidenceDossier: ...


class SpecialistExecutor(Protocol):
    def execute(
        self,
        role: SpecialistRole,
        dossier: ProductEvidenceDossier,
        previous_outputs: Sequence[SpecialistOutput],
    ) -> SpecialistOutput: ...


@dataclass(frozen=True, slots=True)
class CommercialPipelineResult:
    action: CommercialAction
    status: PipelineStatus
    dossier: ProductEvidenceDossier | None
    outputs: tuple[SpecialistOutput, ...]
    errors: tuple[str, ...] = ()
    blocked_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "status": self.status.value,
            "dossier": self.dossier.to_dict() if self.dossier else None,
            "outputs": [output.to_dict() for output in self.outputs],
            "errors": list(self.errors),
            "blocked_reason": self.blocked_reason,
        }


_ACTION_ROLES: Mapping[CommercialAction, tuple[SpecialistRole, ...]] = {
    CommercialAction.ANALYSIS: (
        SpecialistRole.PRODUCT_ANALYST,
        SpecialistRole.COMPETITOR_ANALYST,
        SpecialistRole.REVIEWER,
    ),
    CommercialAction.LISTING: (
        SpecialistRole.PRODUCT_ANALYST,
        SpecialistRole.LISTING_WRITER,
        SpecialistRole.REVIEWER,
    ),
    CommercialAction.VIDEO: (
        SpecialistRole.PRODUCT_ANALYST,
        SpecialistRole.VIDEO_WRITER,
        SpecialistRole.REVIEWER,
    ),
    CommercialAction.STRATEGY: (
        SpecialistRole.PRODUCT_ANALYST,
        SpecialistRole.COMPETITOR_ANALYST,
        SpecialistRole.SALES_STRATEGIST,
        SpecialistRole.REVIEWER,
    ),
    CommercialAction.COMPLETE: (
        SpecialistRole.PRODUCT_ANALYST,
        SpecialistRole.COMPETITOR_ANALYST,
        SpecialistRole.SALES_STRATEGIST,
        SpecialistRole.LISTING_WRITER,
        SpecialistRole.VIDEO_WRITER,
        SpecialistRole.REVIEWER,
    ),
}


def roles_for_action(action: CommercialAction | str) -> tuple[SpecialistRole, ...]:
    return _ACTION_ROLES[CommercialAction(action)]


class CommercialAgentOrchestrator:
    """Executa especialistas em série sobre uma única ficha verificada."""

    def __init__(
        self,
        collector: EvidenceCollector,
        executor: SpecialistExecutor,
        *,
        minimum_verified_claims: int = 1,
    ) -> None:
        if minimum_verified_claims < 1:
            raise ValueError("minimum_verified_claims precisa ser ao menos 1.")
        self.collector = collector
        self.executor = executor
        self.minimum_verified_claims = minimum_verified_claims

    @staticmethod
    def _validate_output(
        output: SpecialistOutput,
        expected_role: SpecialistRole,
        dossier: ProductEvidenceDossier,
    ) -> tuple[str, ...]:
        errors: list[str] = []
        if output.role is not expected_role:
            errors.append(
                f"O especialista {expected_role.value} respondeu como {output.role.value}."
            )
        for assertion in output.assertions:
            unknown = sorted(set(assertion.source_urls) - dossier.source_urls)
            if unknown:
                errors.append(
                    f"{expected_role.value} citou fontes fora da ficha: "
                    + ", ".join(unknown)
                )
            unknown_fields = sorted(set(assertion.claim_fields) - dossier.verified_fields)
            if unknown_fields:
                errors.append(
                    f"{expected_role.value} usou campos não verificados: "
                    + ", ".join(unknown_fields)
                )
        return tuple(errors)

    def run(
        self,
        action: CommercialAction | str,
        subject: str,
    ) -> CommercialPipelineResult:
        selected_action = CommercialAction(action)
        clean_subject = subject.strip()
        if not clean_subject:
            raise ValueError("Informe um produto ou link para iniciar o fluxo.")

        try:
            dossier = self.collector.collect(clean_subject)
        except Exception as exc:
            return CommercialPipelineResult(
                action=selected_action,
                status=PipelineStatus.BLOCKED,
                dossier=None,
                outputs=(),
                errors=(f"Falha no coletor: {type(exc).__name__}: {exc}",),
                blocked_reason="Não foi possível criar a ficha de evidências.",
            )

        return self.run_with_dossier(selected_action, dossier)

    def run_with_dossier(
        self,
        action: CommercialAction | str,
        dossier: ProductEvidenceDossier,
    ) -> CommercialPipelineResult:
        """Executa os especialistas sobre uma ficha previamente aprovada."""

        selected_action = CommercialAction(action)

        if len(dossier.claims) < self.minimum_verified_claims:
            return CommercialPipelineResult(
                action=selected_action,
                status=PipelineStatus.BLOCKED,
                dossier=dossier,
                outputs=(),
                blocked_reason=(
                    "Dados verificados insuficientes. Os especialistas não foram executados."
                ),
            )

        outputs: list[SpecialistOutput] = []
        errors: list[str] = []
        for role in roles_for_action(selected_action):
            try:
                output = self.executor.execute(role, dossier, tuple(outputs))
            except Exception as exc:
                errors.append(f"Falha em {role.value}: {type(exc).__name__}: {exc}")
                break
            validation_errors = self._validate_output(output, role, dossier)
            if validation_errors:
                errors.extend(validation_errors)
                break
            outputs.append(output)

        status = PipelineStatus.COMPLETED if not errors else PipelineStatus.NEEDS_REVIEW
        return CommercialPipelineResult(
            action=selected_action,
            status=status,
            dossier=dossier,
            outputs=tuple(outputs),
            errors=tuple(errors),
            blocked_reason=(
                "Uma saída não passou pela validação de evidências." if errors else ""
            ),
        )


__all__ = [
    "CommercialAction",
    "CommercialAgentOrchestrator",
    "CommercialPipelineResult",
    "EvidenceClaim",
    "EvidenceCollector",
    "EvidenceSource",
    "FactualAssertion",
    "PipelineStatus",
    "ProductEvidenceDossier",
    "SpecialistExecutor",
    "SpecialistOutput",
    "SpecialistRole",
    "roles_for_action",
]
