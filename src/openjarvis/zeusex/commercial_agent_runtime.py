"""Adaptadores de IA e pesquisa para o fluxo comercial especializado."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlparse

from openjarvis.core.types import Message, Role
from openjarvis.engine._stubs import InferenceEngine
from openjarvis.tools.web_search import WebSearchTool
from openjarvis.zeusex.commercial_agents import (
    EvidenceClaim,
    EvidenceSource,
    FactualAssertion,
    ProductEvidenceDossier,
    SpecialistOutput,
    SpecialistRole,
)


_ROLE_INSTRUCTIONS: Mapping[SpecialistRole, str] = {
    SpecialistRole.PRODUCT_ANALYST: (
        "Analise problema resolvido, público, benefícios, limitações, objeções e risco de devolução."
    ),
    SpecialistRole.COMPETITOR_ANALYST: (
        "Compare somente concorrentes presentes na ficha e destaque lacunas sem estimar métricas."
    ),
    SpecialistRole.SALES_STRATEGIST: (
        "Proponha posicionamento, canais, kits, upsell e próximos testes; diferencie fato de hipótese."
    ),
    SpecialistRole.LISTING_WRITER: (
        "Crie títulos, descrição, atributos e CTA sem transformar hipótese em característica do produto."
    ),
    SpecialistRole.VIDEO_WRITER: (
        "Crie roteiros de 15, 30 e 60 segundos, cenas e CTA sem simular depoimentos."
    ),
    SpecialistRole.REVIEWER: (
        "Audite as saídas anteriores. Aponte invenções, promessas absolutas, contradições e fontes ausentes."
    ),
}

_ROLE_MODEL_ENV: Mapping[SpecialistRole, str] = {
    SpecialistRole.PRODUCT_ANALYST: "ZEUSEX_COMMERCIAL_PRODUCT_ANALYST_MODEL",
    SpecialistRole.COMPETITOR_ANALYST: "ZEUSEX_COMMERCIAL_COMPETITOR_ANALYST_MODEL",
    SpecialistRole.SALES_STRATEGIST: "ZEUSEX_COMMERCIAL_SALES_STRATEGIST_MODEL",
    SpecialistRole.LISTING_WRITER: "ZEUSEX_COMMERCIAL_LISTING_WRITER_MODEL",
    SpecialistRole.VIDEO_WRITER: "ZEUSEX_COMMERCIAL_VIDEO_WRITER_MODEL",
    SpecialistRole.REVIEWER: "ZEUSEX_COMMERCIAL_REVIEWER_MODEL",
}

_OPENROUTER_FREE_MODEL = "openrouter/openrouter/free"


@dataclass(frozen=True, slots=True)
class CommercialModelPolicy:
    """Escolhe modelos por função sem armazenar chaves ou nomes no código."""

    fallback_model: str
    collector_model: str
    role_models: Mapping[SpecialistRole, str]

    @classmethod
    def from_env(cls, default_model: str) -> "CommercialModelPolicy":
        fallback = default_model.strip()
        if not fallback:
            raise ValueError("O modelo de retorno local não foi configurado.")
        preferred_default = (
            _OPENROUTER_FREE_MODEL
            if os.getenv("OPENROUTER_API_KEY", "").strip()
            else fallback
        )
        collector = os.getenv("ZEUSEX_COMMERCIAL_COLLECTOR_MODEL", "").strip()
        return cls(
            fallback_model=fallback,
            collector_model=collector or preferred_default,
            role_models={
                role: os.getenv(variable, "").strip() or preferred_default
                for role, variable in _ROLE_MODEL_ENV.items()
            },
        )

    def role_model(self, role: SpecialistRole) -> str:
        return self.role_models.get(role, self.fallback_model)


def _json_object(text: str) -> dict[str, Any]:
    """Lê um único objeto JSON, aceitando apenas cercas Markdown externas."""

    clean = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", clean, re.DOTALL)
    if fenced:
        clean = fenced.group(1)
    try:
        value = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError("O modelo não retornou JSON válido.") from exc
    if not isinstance(value, dict):
        raise ValueError("O modelo precisa retornar um objeto JSON.")
    return value


def _string_tuple(value: Any, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} precisa ser uma lista de textos.")
    return tuple(item.strip() for item in value if item.strip())


@dataclass(slots=True)
class EngineSpecialistExecutor:
    engine: InferenceEngine
    model: str
    max_tokens: int = 2500

    def execute(
        self,
        role: SpecialistRole,
        dossier: ProductEvidenceDossier,
        previous_outputs: Sequence[SpecialistOutput],
    ) -> SpecialistOutput:
        payload = {
            "ficha_verificada": dossier.to_dict(),
            "saidas_anteriores": [output.to_dict() for output in previous_outputs],
        }
        system = f"""Você é o especialista {role.value} do Achadinhos do JR.
{_ROLE_INSTRUCTIONS[role]}

REGRAS INEGOCIÁVEIS:
- Use somente fatos presentes em ficha_verificada.claims.
- Um campo ausente continua ausente; não estime preço, vendas, nota ou avaliação.
- Não crie depoimentos, citações de compradores ou testes que não estejam na ficha.
- Toda afirmação factual deve aparecer em assertions com uma URL e os claim_fields exatos da ficha.
- Ideias comerciais e inferências devem aparecer em assumptions.
- Responda somente JSON no formato:
{{"content":"texto em português do Brasil","assertions":[{{"text":"fato","source_urls":["https://..."],"claim_fields":["product.name"]}}],"assumptions":[],"missing_information":[]}}
"""
        response = self.engine.generate(
            [
                Message(Role.SYSTEM, system),
                Message(Role.USER, json.dumps(payload, ensure_ascii=False)),
            ],
            model=self.model,
            temperature=0.2 if role is SpecialistRole.REVIEWER else 0.4,
            max_tokens=self.max_tokens,
        )
        parsed = _json_object(str(response.get("content", "")))
        content = parsed.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("O especialista não retornou content válido.")

        raw_assertions = parsed.get("assertions", [])
        if not isinstance(raw_assertions, list):
            raise ValueError("assertions precisa ser uma lista.")
        assertions: list[FactualAssertion] = []
        for item in raw_assertions:
            if not isinstance(item, Mapping) or not isinstance(item.get("text"), str):
                raise ValueError("Cada assertion precisa conter text e source_urls.")
            assertions.append(
                FactualAssertion(
                    item["text"],
                    _string_tuple(item.get("source_urls"), field="source_urls"),
                    _string_tuple(item.get("claim_fields"), field="claim_fields"),
                )
            )
        return SpecialistOutput(
            role=role,
            content=content,
            assertions=tuple(assertions),
            assumptions=_string_tuple(parsed.get("assumptions"), field="assumptions"),
            missing_information=_string_tuple(
                parsed.get("missing_information"), field="missing_information"
            ),
            model=self.model,
        )


@dataclass(slots=True)
class RoutedSpecialistExecutor:
    """Executa cada função no modelo escolhido e retorna ao modelo principal."""

    engine: InferenceEngine
    policy: CommercialModelPolicy

    def execute(
        self,
        role: SpecialistRole,
        dossier: ProductEvidenceDossier,
        previous_outputs: Sequence[SpecialistOutput],
    ) -> SpecialistOutput:
        preferred = self.policy.role_model(role)
        try:
            return EngineSpecialistExecutor(self.engine, preferred).execute(
                role, dossier, previous_outputs
            )
        except Exception:
            fallback = self.policy.fallback_model
            if preferred == fallback:
                raise
            try:
                return EngineSpecialistExecutor(self.engine, fallback).execute(
                    role, dossier, previous_outputs
                )
            except Exception as fallback_error:
                raise RuntimeError(
                    f"O especialista {role.value} falhou nos modelos "
                    f"{preferred!r} e {fallback!r}."
                ) from fallback_error


@dataclass(slots=True)
class EngineEvidenceCollector:
    """Pesquisa o produto e pede ao modelo apenas a extração de fatos citados."""

    engine: InferenceEngine
    model: str
    search: WebSearchTool
    max_tokens: int = 2200

    def _extract(
        self,
        subject: str,
        documents: Sequence[tuple[str, str, str]],
    ) -> ProductEvidenceDossier:
        prompt = {
            "produto_ou_link": subject,
            "fontes_permitidas": [
                {"url": url, "title": title, "content": content}
                for url, title, content in documents
            ],
        }
        system = """Você é o Coletor de Evidências do Achadinhos do JR.
Extraia somente fatos explícitos nos documentos fornecidos. Não interprete avaliações,
não complete lacunas e não crie citações. Use nomes de campo estáveis, como product.name,
product.price, product.rating, product.sales, product.specification.<nome> e
competitor.<n>.<campo>. Cada claim deve citar apenas URLs de fontes_permitidas.
Responda somente JSON:
{"claims":[{"field":"product.name","value":"...","source_urls":["https://..."]}],
 "missing_fields":[],"warnings":[]}
"""
        response = self.engine.generate(
            [
                Message(Role.SYSTEM, system),
                Message(Role.USER, json.dumps(prompt, ensure_ascii=False)),
            ],
            model=self.model,
            temperature=0.0,
            max_tokens=self.max_tokens,
        )
        parsed = _json_object(str(response.get("content", "")))
        raw_claims = parsed.get("claims", [])
        if not isinstance(raw_claims, list):
            raise ValueError("claims precisa ser uma lista.")
        claims: list[EvidenceClaim] = []
        for item in raw_claims:
            if not isinstance(item, Mapping):
                raise ValueError("Cada claim precisa ser um objeto.")
            field_name = item.get("field")
            if not isinstance(field_name, str):
                raise ValueError("Cada claim precisa de field textual.")
            claims.append(
                EvidenceClaim(
                    field_name,
                    item.get("value"),
                    _string_tuple(item.get("source_urls"), field="source_urls"),
                )
            )
        retrieved_at = datetime.now(timezone.utc).isoformat()
        return ProductEvidenceDossier(
            subject=subject,
            sources=tuple(
                EvidenceSource(url, title, retrieved_at) for url, title, _ in documents
            ),
            claims=tuple(claims),
            missing_fields=_string_tuple(
                parsed.get("missing_fields"), field="missing_fields"
            ),
            warnings=_string_tuple(parsed.get("warnings"), field="warnings"),
            collector_model=self.model,
        )

    @staticmethod
    def _search_documents(result: Any, subject: str) -> tuple[tuple[str, str, str], ...]:
        if not result.success:
            return ()
        metadata_url = result.metadata.get("url") if isinstance(result.metadata, Mapping) else None
        if isinstance(metadata_url, str):
            return ((metadata_url, subject, result.content),)

        parts = re.split(r"\n\s*---\s*\n", result.content)
        documents: list[tuple[str, str, str]] = []
        for part in parts:
            url_match = re.search(r"^Source:\s*(https?://\S+)", part, re.MULTILINE)
            if not url_match:
                continue
            title_match = re.search(r"^###\s+(.+)$", part, re.MULTILINE)
            documents.append(
                (
                    url_match.group(1).rstrip(".,;)"),
                    title_match.group(1).strip() if title_match else "Resultado",
                    part.strip(),
                )
            )
        return tuple(documents)

    def collect_documents(self, subject: str) -> tuple[tuple[str, str, str], ...]:
        """Pesquisa uma vez e devolve o conjunto deduplicado de fontes."""

        result = self.search.execute(query=subject, max_results=8)
        documents = list(self._search_documents(result, subject))
        parsed_subject = urlparse(subject)
        if parsed_subject.scheme in {"http", "https"}:
            words = re.sub(
                r"\b(?:p|produto|item|mlb)\b|\d{5,}",
                " ",
                unquote(parsed_subject.path).replace("-", " "),
                flags=re.IGNORECASE,
            )
            discovery_query = " ".join(words.split())
            if discovery_query:
                discovery = self.search.execute(
                    query=f"{discovery_query} concorrentes similares preço",
                    max_results=8,
                )
                documents.extend(self._search_documents(discovery, discovery_query))
        unique_documents = tuple(
            {document[0]: document for document in documents}.values()
        )
        if not unique_documents:
            raise ValueError("A pesquisa não retornou nenhuma fonte verificável.")
        return unique_documents

    def collect(self, subject: str) -> ProductEvidenceDossier:
        return self._extract(subject, self.collect_documents(subject))


@dataclass(slots=True)
class RoutedEvidenceCollector:
    """Usa o coletor preferido e retorna ao modelo principal em caso de falha."""

    engine: InferenceEngine
    policy: CommercialModelPolicy
    search: WebSearchTool

    def collect(self, subject: str) -> ProductEvidenceDossier:
        preferred = self.policy.collector_model
        collector = EngineEvidenceCollector(self.engine, preferred, self.search)
        documents = collector.collect_documents(subject)
        try:
            return collector._extract(subject, documents)
        except Exception:
            fallback = self.policy.fallback_model
            if preferred == fallback:
                raise
            try:
                return EngineEvidenceCollector(
                    self.engine, fallback, self.search
                )._extract(subject, documents)
            except Exception as fallback_error:
                raise RuntimeError(
                    f"A coleta falhou nos modelos {preferred!r} e {fallback!r}."
                ) from fallback_error


__all__ = [
    "CommercialModelPolicy",
    "EngineEvidenceCollector",
    "EngineSpecialistExecutor",
    "RoutedEvidenceCollector",
    "RoutedSpecialistExecutor",
]
