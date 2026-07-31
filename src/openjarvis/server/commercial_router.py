"""Rotas do orquestrador de especialistas do Achadinhos do JR."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from openjarvis.tools.web_search import WebSearchTool
from openjarvis.zeusex.commercial_agent_runtime import (
    CommercialModelPolicy,
    RoutedEvidenceCollector,
    RoutedSpecialistExecutor,
)
from openjarvis.zeusex.commercial_agents import (
    CommercialAction,
    CommercialAgentOrchestrator,
    EvidenceClaim,
    EvidenceSource,
    ProductEvidenceDossier,
)

router = APIRouter(prefix="/v1/commercial", tags=["commercial"])


class CommercialCollectionRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=10_000)
    model: str = ""


class CommercialOrchestrationRequest(BaseModel):
    action: CommercialAction
    dossier: dict[str, Any]
    model: str = ""


def _engine_and_model(request: Request, requested_model: str) -> tuple[Any, str]:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Motor de IA indisponível.")
    model = requested_model.strip() or str(getattr(request.app.state, "model", ""))
    if not model:
        raise HTTPException(status_code=503, detail="Nenhum modelo foi configurado.")
    return engine, model


def _string_items(value: Any, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} precisa ser uma lista de textos.")
    return tuple(item for item in value if item.strip())


def _dossier_from_dict(value: dict[str, Any]) -> ProductEvidenceDossier:
    """Reconstrói e revalida a ficha recebida da interface."""

    sources = value.get("sources")
    claims = value.get("claims")
    if not isinstance(sources, list) or not isinstance(claims, list):
        raise HTTPException(
            status_code=422,
            detail="Ficha de evidências inválida: sources e claims são obrigatórios.",
        )
    try:
        return ProductEvidenceDossier(
            subject=str(value.get("subject", "")),
            sources=tuple(
                EvidenceSource(
                    url=str(item.get("url", "")),
                    title=str(item.get("title", "")),
                    retrieved_at=str(item.get("retrieved_at", "")),
                )
                for item in sources
                if isinstance(item, dict)
            ),
            claims=tuple(
                EvidenceClaim(
                    field=str(item.get("field", "")),
                    value=item.get("value"),
                    source_urls=_string_items(
                        item.get("source_urls"), field="source_urls"
                    ),
                )
                for item in claims
                if isinstance(item, dict)
            ),
            missing_fields=_string_items(
                value.get("missing_fields", []), field="missing_fields"
            ),
            warnings=_string_items(value.get("warnings", []), field="warnings"),
            collector_model=str(value.get("collector_model", "")),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Ficha de evidências inválida: {exc}",
        ) from exc


@router.post("/collect")
def collect_commercial_evidence(
    payload: CommercialCollectionRequest,
    request: Request,
) -> dict:
    """Cria a ficha que o usuário deve revisar antes de autorizar os bots."""

    engine, model = _engine_and_model(request, payload.model)
    policy = CommercialModelPolicy.from_env(model)
    try:
        return RoutedEvidenceCollector(
            engine,
            policy,
            WebSearchTool(max_results=8),
        ).collect(payload.subject).to_dict()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/orchestrate")
def orchestrate_commercial(
    payload: CommercialOrchestrationRequest,
    request: Request,
) -> dict:
    """Executa somente a ficha que já foi apresentada e aprovada."""

    engine, model = _engine_and_model(request, payload.model)
    policy = CommercialModelPolicy.from_env(model)
    dossier = _dossier_from_dict(payload.dossier)
    pipeline = CommercialAgentOrchestrator(
        RoutedEvidenceCollector(engine, policy, WebSearchTool(max_results=8)),
        RoutedSpecialistExecutor(engine, policy),
    )
    return pipeline.run_with_dossier(payload.action, dossier).to_dict()


__all__ = [
    "CommercialCollectionRequest",
    "CommercialOrchestrationRequest",
    "router",
]
