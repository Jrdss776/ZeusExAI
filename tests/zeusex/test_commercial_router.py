"""Testes da rota que liga a Central Comercial ao orquestrador."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi", reason="openjarvis[server] not installed")

from fastapi import HTTPException  # noqa: E402

from openjarvis.core.types import ToolResult  # noqa: E402
from openjarvis.server import commercial_router  # noqa: E402
from openjarvis.server.commercial_router import (  # noqa: E402
    CommercialCollectionRequest,
    CommercialOrchestrationRequest,
)


URL = "https://example.com/produto-teste"


class SequencedEngine:
    def __init__(self):
        self.responses = [
            {
                "claims": [
                    {"field": "product.name", "value": "Produto", "source_urls": [URL]}
                ],
                "missing_fields": ["product.sales"],
                "warnings": [],
            },
            {
                "content": "Análise",
                "assertions": [],
                "assumptions": [],
                "missing_information": [],
            },
            {
                "content": "Concorrência",
                "assertions": [],
                "assumptions": [],
                "missing_information": [],
            },
            {
                "content": "Revisão",
                "assertions": [],
                "assumptions": [],
                "missing_information": [],
            },
        ]

    def generate(self, messages, **kwargs):
        del messages, kwargs
        return {"content": json.dumps(self.responses.pop(0))}


class SuccessfulSearch:
    def __init__(self, max_results=8):
        del max_results

    def execute(self, **kwargs):
        del kwargs
        return ToolResult(
            "web_search",
            "Conteúdo verificável",
            metadata={"url": URL, "mode": "fetch"},
        )


def _request(engine):
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(engine=engine, model="modelo-local"))
    )


def test_route_executes_analysis_specialists(monkeypatch) -> None:
    monkeypatch.setattr(commercial_router, "WebSearchTool", SuccessfulSearch)
    engine = SequencedEngine()
    dossier = commercial_router.collect_commercial_evidence(
        CommercialCollectionRequest(subject=URL),
        _request(engine),
    )

    assert dossier["claims"][0]["field"] == "product.name"
    assert dossier["missing_fields"] == ["product.sales"]

    result = commercial_router.orchestrate_commercial(
        CommercialOrchestrationRequest(action="analysis", dossier=dossier),
        _request(engine),
    )

    assert result["status"] == "completed"
    assert [output["role"] for output in result["outputs"]] == [
        "product_analyst",
        "competitor_analyst",
        "reviewer",
    ]
    assert result["dossier"]["missing_fields"] == ["product.sales"]


def test_route_rejects_missing_engine() -> None:
    with pytest.raises(HTTPException) as exc_info:
        commercial_router.collect_commercial_evidence(
            CommercialCollectionRequest(subject=URL),
            _request(None),
        )
    assert exc_info.value.status_code == 503


def test_route_revalidates_approved_dossier() -> None:
    tampered = {
        "subject": URL,
        "sources": [{"url": URL, "title": "Produto", "retrieved_at": ""}],
        "claims": [
            {
                "field": "product.rating",
                "value": "5.0",
                "source_urls": ["https://inventado.invalid/review"],
            }
        ],
        "missing_fields": [],
        "warnings": [],
    }
    with pytest.raises(HTTPException) as exc_info:
        commercial_router.orchestrate_commercial(
            CommercialOrchestrationRequest(action="analysis", dossier=tampered),
            _request(SequencedEngine()),
        )
    assert exc_info.value.status_code == 422
    assert "fontes não cadastradas" in exc_info.value.detail
