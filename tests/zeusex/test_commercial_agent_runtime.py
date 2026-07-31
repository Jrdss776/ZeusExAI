"""Testes dos adaptadores de IA do fluxo comercial."""

from __future__ import annotations

import json

import pytest

from openjarvis.core.types import ToolResult
from openjarvis.zeusex.commercial_agent_runtime import (
    CommercialModelPolicy,
    EngineEvidenceCollector,
    EngineSpecialistExecutor,
    RoutedEvidenceCollector,
    RoutedSpecialistExecutor,
)
from openjarvis.zeusex.commercial_agents import (
    EvidenceClaim,
    EvidenceSource,
    ProductEvidenceDossier,
    SpecialistRole,
)


URL = "https://example.com/produto"


class FakeEngine:
    def __init__(self, payload, failing_models=()):
        self.payload = payload
        self.failing_models = set(failing_models)
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if kwargs.get("model") in self.failing_models:
            raise RuntimeError("modelo indisponível")
        content = self.payload if isinstance(self.payload, str) else json.dumps(self.payload)
        return {"content": content}


class FakeSearch:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _dossier():
    return ProductEvidenceDossier(
        subject=URL,
        sources=(EvidenceSource(URL),),
        claims=(EvidenceClaim("product.name", "Produto real", (URL,)),),
    )


def test_specialist_parses_strict_grounded_json() -> None:
    engine = FakeEngine(
        {
            "content": "Análise pronta",
            "assertions": [
                {
                    "text": "Nome confirmado",
                    "source_urls": [URL],
                    "claim_fields": ["product.name"],
                }
            ],
            "assumptions": ["Testar o criativo"],
            "missing_information": ["Vendas"],
        }
    )
    output = EngineSpecialistExecutor(engine, "modelo").execute(
        SpecialistRole.PRODUCT_ANALYST, _dossier(), ()
    )

    assert output.role is SpecialistRole.PRODUCT_ANALYST
    assert output.assertions[0].source_urls == (URL,)
    assert output.assertions[0].claim_fields == ("product.name",)
    assert output.model == "modelo"
    assert engine.calls[0][1]["temperature"] == 0.4
    assert "Não crie depoimentos" in engine.calls[0][0][0].content


def test_specialist_rejects_plain_text_instead_of_silently_accepting_it() -> None:
    with pytest.raises(ValueError, match="JSON válido"):
        EngineSpecialistExecutor(FakeEngine("parece uma resposta"), "modelo").execute(
            SpecialistRole.PRODUCT_ANALYST, _dossier(), ()
        )


def test_collector_builds_dossier_only_from_returned_source() -> None:
    search = FakeSearch(
        ToolResult(
            "web_search",
            "Página do produto",
            metadata={"url": URL, "mode": "fetch"},
        )
    )
    engine = FakeEngine(
        {
            "claims": [
                {"field": "product.name", "value": "Produto real", "source_urls": [URL]}
            ],
            "missing_fields": ["product.sales"],
            "warnings": [],
        }
    )

    dossier = EngineEvidenceCollector(engine, "modelo", search).collect(URL)

    assert dossier.claims[0].value == "Produto real"
    assert dossier.missing_fields == ("product.sales",)
    assert dossier.sources[0].url == URL
    assert dossier.collector_model == "modelo"


def test_collector_rejects_model_source_not_seen_by_search() -> None:
    search = FakeSearch(
        ToolResult("web_search", "Página", metadata={"url": URL, "mode": "fetch"})
    )
    engine = FakeEngine(
        {
            "claims": [
                {
                    "field": "product.rating",
                    "value": "5.0",
                    "source_urls": ["https://inventado.invalid/review"],
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="fontes não cadastradas"):
        EngineEvidenceCollector(engine, "modelo", search).collect(URL)


def test_collector_blocks_when_search_has_no_verifiable_source() -> None:
    search = FakeSearch(ToolResult("web_search", "falhou", success=False))
    with pytest.raises(ValueError, match="fonte verificável"):
        EngineEvidenceCollector(FakeEngine({}), "modelo", search).collect(URL)


def test_model_policy_reads_one_model_per_specialist(monkeypatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("ZEUSEX_COMMERCIAL_COLLECTOR_MODEL", "openrouter/coletor")
    monkeypatch.setenv("ZEUSEX_COMMERCIAL_REVIEWER_MODEL", "openrouter/revisor")

    policy = CommercialModelPolicy.from_env("local/qwen")

    assert policy.collector_model == "openrouter/coletor"
    assert policy.role_model(SpecialistRole.REVIEWER) == "openrouter/revisor"
    assert policy.role_model(SpecialistRole.PRODUCT_ANALYST) == "local/qwen"


def test_model_policy_uses_free_router_when_key_is_available(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "segredo-nao-exposto")
    for variable in (
        "ZEUSEX_COMMERCIAL_COLLECTOR_MODEL",
        "ZEUSEX_COMMERCIAL_PRODUCT_ANALYST_MODEL",
        "ZEUSEX_COMMERCIAL_REVIEWER_MODEL",
    ):
        monkeypatch.delenv(variable, raising=False)

    policy = CommercialModelPolicy.from_env("qwen2.5:3b")

    assert policy.fallback_model == "qwen2.5:3b"
    assert policy.collector_model == "openrouter/openrouter/free"
    assert (
        policy.role_model(SpecialistRole.PRODUCT_ANALYST)
        == "openrouter/openrouter/free"
    )
    assert policy.role_model(SpecialistRole.REVIEWER) == "openrouter/openrouter/free"


def test_routed_specialist_falls_back_and_records_used_model() -> None:
    payload = {
        "content": "Análise pronta",
        "assertions": [],
        "assumptions": [],
        "missing_information": [],
    }
    engine = FakeEngine(payload, failing_models={"openrouter/especialista"})
    policy = CommercialModelPolicy(
        fallback_model="local/qwen",
        collector_model="local/qwen",
        role_models={SpecialistRole.PRODUCT_ANALYST: "openrouter/especialista"},
    )

    output = RoutedSpecialistExecutor(engine, policy).execute(
        SpecialistRole.PRODUCT_ANALYST, _dossier(), ()
    )

    assert [call[1]["model"] for call in engine.calls] == [
        "openrouter/especialista",
        "local/qwen",
    ]
    assert output.model == "local/qwen"


def test_routed_collector_falls_back_and_records_used_model() -> None:
    payload = {
        "claims": [
            {"field": "product.name", "value": "Produto real", "source_urls": [URL]}
        ],
        "missing_fields": [],
        "warnings": [],
    }
    engine = FakeEngine(payload, failing_models={"openrouter/coletor"})
    search = FakeSearch(
        ToolResult("web_search", "Página", metadata={"url": URL, "mode": "fetch"})
    )
    policy = CommercialModelPolicy(
        fallback_model="local/qwen",
        collector_model="openrouter/coletor",
        role_models={},
    )

    dossier = RoutedEvidenceCollector(engine, policy, search).collect("produto teste")

    assert [call[1]["model"] for call in engine.calls] == [
        "openrouter/coletor",
        "local/qwen",
    ]
    assert len(search.calls) == 1
    assert dossier.collector_model == "local/qwen"
