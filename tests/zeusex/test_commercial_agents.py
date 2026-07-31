"""Testes adversariais do orquestrador comercial especializado."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from openjarvis.zeusex.commercial_agents import (
    CommercialAction,
    CommercialAgentOrchestrator,
    EvidenceClaim,
    EvidenceSource,
    FactualAssertion,
    PipelineStatus,
    ProductEvidenceDossier,
    SpecialistOutput,
    SpecialistRole,
    roles_for_action,
)


SOURCE_URL = "https://example.com/produto"


def _dossier(*, claims: bool = True) -> ProductEvidenceDossier:
    return ProductEvidenceDossier(
        subject=SOURCE_URL,
        sources=(EvidenceSource(SOURCE_URL, "Produto"),),
        claims=(EvidenceClaim("name", "Produto verificado", (SOURCE_URL,)),)
        if claims
        else (),
        missing_fields=("sales", "ratings"),
    )


@dataclass
class FakeCollector:
    dossier: ProductEvidenceDossier
    calls: list[str] = field(default_factory=list)

    def collect(self, subject: str) -> ProductEvidenceDossier:
        self.calls.append(subject)
        return self.dossier


@dataclass
class FakeExecutor:
    bad_source_for: SpecialistRole | None = None
    fail_for: SpecialistRole | None = None
    calls: list[SpecialistRole] = field(default_factory=list)

    def execute(self, role, dossier, previous_outputs):
        del dossier, previous_outputs
        self.calls.append(role)
        if role is self.fail_for:
            raise RuntimeError("provedor indisponível")
        source = "https://inventado.invalid/avaliacao" if role is self.bad_source_for else SOURCE_URL
        return SpecialistOutput(
            role=role,
            content=f"Saída de {role.value}",
            assertions=(FactualAssertion("Fato usado", (source,), ("name",)),),
        )


def test_analysis_runs_collector_before_only_required_specialists() -> None:
    collector = FakeCollector(_dossier())
    executor = FakeExecutor()

    result = CommercialAgentOrchestrator(collector, executor).run(
        CommercialAction.ANALYSIS,
        SOURCE_URL,
    )

    assert result.status is PipelineStatus.COMPLETED
    assert collector.calls == [SOURCE_URL]
    assert executor.calls == list(roles_for_action(CommercialAction.ANALYSIS))
    assert SpecialistRole.LISTING_WRITER not in executor.calls
    assert executor.calls[-1] is SpecialistRole.REVIEWER


def test_approved_dossier_does_not_trigger_a_second_collection() -> None:
    collector = FakeCollector(_dossier())
    executor = FakeExecutor()

    result = CommercialAgentOrchestrator(collector, executor).run_with_dossier(
        CommercialAction.LISTING,
        _dossier(),
    )

    assert result.status is PipelineStatus.COMPLETED
    assert collector.calls == []


def test_no_specialist_runs_without_verified_evidence() -> None:
    executor = FakeExecutor()
    result = CommercialAgentOrchestrator(
        FakeCollector(_dossier(claims=False)), executor
    ).run(CommercialAction.COMPLETE, SOURCE_URL)

    assert result.status is PipelineStatus.BLOCKED
    assert "insuficientes" in result.blocked_reason
    assert executor.calls == []


def test_dossier_rejects_claim_tied_to_unknown_source() -> None:
    with pytest.raises(ValueError, match="fontes não cadastradas"):
        ProductEvidenceDossier(
            subject=SOURCE_URL,
            sources=(EvidenceSource(SOURCE_URL),),
            claims=(
                EvidenceClaim(
                    "rating",
                    "5.0",
                    ("https://inventado.invalid/avaliacao",),
                ),
            ),
        )


def test_pipeline_stops_before_reviewer_on_invented_source() -> None:
    executor = FakeExecutor(bad_source_for=SpecialistRole.PRODUCT_ANALYST)
    result = CommercialAgentOrchestrator(
        FakeCollector(_dossier()), executor
    ).run(CommercialAction.COMPLETE, SOURCE_URL)

    assert result.status is PipelineStatus.NEEDS_REVIEW
    assert "fontes fora da ficha" in result.errors[0]
    assert executor.calls == [SpecialistRole.PRODUCT_ANALYST]
    assert result.outputs == ()


def test_pipeline_rejects_assertion_based_on_unverified_field() -> None:
    class InventedMetricExecutor(FakeExecutor):
        def execute(self, role, dossier, previous_outputs):
            del dossier, previous_outputs
            self.calls.append(role)
            return SpecialistOutput(
                role=role,
                content="O produto possui milhares de vendas.",
                assertions=(
                    FactualAssertion(
                        "Milhares de vendas",
                        (SOURCE_URL,),
                        ("sales",),
                    ),
                ),
            )

    result = CommercialAgentOrchestrator(
        FakeCollector(_dossier()), InventedMetricExecutor()
    ).run(CommercialAction.ANALYSIS, SOURCE_URL)

    assert result.status is PipelineStatus.NEEDS_REVIEW
    assert "campos não verificados: sales" in result.errors[0]


def test_provider_failure_returns_partial_auditable_result() -> None:
    executor = FakeExecutor(fail_for=SpecialistRole.SALES_STRATEGIST)
    result = CommercialAgentOrchestrator(
        FakeCollector(_dossier()), executor
    ).run(CommercialAction.STRATEGY, SOURCE_URL)

    assert result.status is PipelineStatus.NEEDS_REVIEW
    assert [output.role for output in result.outputs] == [
        SpecialistRole.PRODUCT_ANALYST,
        SpecialistRole.COMPETITOR_ANALYST,
    ]
    assert "provedor indisponível" in result.errors[0]
    assert SpecialistRole.REVIEWER not in executor.calls


def test_every_action_finishes_with_independent_reviewer() -> None:
    for action in CommercialAction:
        assert roles_for_action(action)[-1] is SpecialistRole.REVIEWER


def test_source_requires_real_http_url() -> None:
    with pytest.raises(ValueError, match="HTTP"):
        EvidenceSource("texto sem URL")


def test_empty_subject_is_rejected_before_collection() -> None:
    collector = FakeCollector(_dossier())
    with pytest.raises(ValueError, match="produto ou link"):
        CommercialAgentOrchestrator(collector, FakeExecutor()).run(
            CommercialAction.ANALYSIS,
            "   ",
        )
    assert collector.calls == []
