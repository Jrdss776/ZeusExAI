"""Camada de serviço JSON para a interface Android local."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, urlsplit

from openjarvis.zeusex.achadinhos_pipeline import (
    AchadinhosSelectionPolicy,
    build_achadinhos_campaigns,
)
from openjarvis.zeusex.analysis_360 import analysis_360_from_mapping
from openjarvis.zeusex.analysis_queue import AnalysisQueue
from openjarvis.zeusex.auth import LocalAPIAuthenticator
from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.campaigns import CatalogItem, campaign_from_mapping
from openjarvis.zeusex.commercial_analysis import CommercialCosts
from openjarvis.zeusex.commercial_batch import (
    CommercialBatchRequest,
    CommercialBatchService,
)
from openjarvis.zeusex.google_calendar import GoogleCalendarService
from openjarvis.zeusex.google_calendar_api import GoogleCalendarAPI
from openjarvis.zeusex.gmail import GmailService
from openjarvis.zeusex.gmail_api import GmailAPI
from openjarvis.zeusex.marketplace import PotentialSignals
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


@dataclass(frozen=True, slots=True)
class APIResponse:
    status: int
    body: dict[str, Any]


def _mapping(value: object, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} precisa ser um objeto.")
    return value


def _mapping_of_mappings(value: object, *, field: str) -> dict[str, Mapping[str, Any]]:
    source = _mapping(value, field=field)
    result: dict[str, Mapping[str, Any]] = {}
    for key, item in source.items():
        result[str(key)] = _mapping(item, field=f"{field}.{key}")
    return result


def _sequence_of_mappings(value: object, *, field: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{field} precisa ser uma lista.")
    result: list[Mapping[str, Any]] = []
    for index, item in enumerate(value):
        result.append(_mapping(item, field=f"{field}[{index}]"))
    return tuple(result)


def _achadinhos_request(payload: Mapping[str, Any]) -> tuple[
    CommercialBatchRequest,
    AchadinhosSelectionPolicy,
    dict[str, tuple[CatalogItem, ...]],
]:
    marketplace = str(payload.get("marketplace") or "")
    marketplace_payload = _mapping(payload.get("payload"), field="payload")

    raw_costs = _mapping_of_mappings(
        payload.get("costs_by_listing") or {},
        field="costs_by_listing",
    )
    costs_by_listing = {
        listing_id: CommercialCosts(**dict(costs))
        for listing_id, costs in raw_costs.items()
    }

    default_costs_data = payload.get("default_costs")
    default_costs = (
        CommercialCosts(**dict(_mapping(default_costs_data, field="default_costs")))
        if default_costs_data is not None
        else None
    )

    raw_attributes = _mapping_of_mappings(
        payload.get("attributes_by_listing") or {},
        field="attributes_by_listing",
    )
    attributes_by_listing = {
        listing_id: {str(key): str(value) for key, value in attributes.items()}
        for listing_id, attributes in raw_attributes.items()
    }

    raw_signals = _mapping_of_mappings(
        payload.get("signals_by_listing") or {},
        field="signals_by_listing",
    )
    signals_by_listing = {
        listing_id: PotentialSignals(**dict(signals))
        for listing_id, signals in raw_signals.items()
    }

    raw_competitors = _mapping(
        payload.get("competitors_by_listing") or {},
        field="competitors_by_listing",
    )
    competitors_by_listing = {
        str(listing_id): _sequence_of_mappings(
            competitors,
            field=f"competitors_by_listing.{listing_id}",
        )
        for listing_id, competitors in raw_competitors.items()
    }

    policy_data = _mapping(payload.get("policy") or {}, field="policy")
    normalized_policy = dict(policy_data)
    allowed = normalized_policy.get("allowed_classifications")
    if allowed is not None:
        if not isinstance(allowed, Sequence) or isinstance(allowed, (str, bytes, bytearray)):
            raise ValueError("policy.allowed_classifications precisa ser uma lista.")
        normalized_policy["allowed_classifications"] = frozenset(str(item) for item in allowed)
    policy = AchadinhosSelectionPolicy(**normalized_policy)

    raw_catalog = _mapping(
        payload.get("catalog_by_listing") or {},
        field="catalog_by_listing",
    )
    catalog_by_listing: dict[str, tuple[CatalogItem, ...]] = {}
    for listing_id, items in raw_catalog.items():
        catalog_items = []
        for index, item in enumerate(
            _sequence_of_mappings(items, field=f"catalog_by_listing.{listing_id}")
        ):
            normalized = dict(item)
            complements = normalized.get("complements") or ()
            if not isinstance(complements, Sequence) or isinstance(
                complements,
                (str, bytes, bytearray),
            ):
                raise ValueError(
                    f"catalog_by_listing.{listing_id}[{index}].complements precisa ser uma lista."
                )
            normalized["complements"] = tuple(str(value) for value in complements)
            catalog_items.append(CatalogItem(**normalized))
        catalog_by_listing[str(listing_id)] = tuple(catalog_items)

    request = CommercialBatchRequest(
        marketplace=marketplace,
        payload=marketplace_payload,
        costs_by_listing=costs_by_listing,
        default_costs=default_costs,
        attributes_by_listing=attributes_by_listing,
        signals_by_listing=signals_by_listing,
        competitors_by_listing=competitors_by_listing,
    )
    return request, policy, catalog_by_listing


class MobileAPIService:
    """Despacha operações locais e não publica conteúdo externamente."""

    def __init__(
        self,
        reports: AnalysisReportStore,
        templates: CampaignTemplateStore,
        scheduler: SafeScheduler,
        *,
        queue: AnalysisQueue | None = None,
        authenticator: LocalAPIAuthenticator | None = None,
        calendar_api: GoogleCalendarAPI | None = None,
        gmail_api: GmailAPI | None = None,
    ) -> None:
        self.reports = reports
        self.templates = templates
        self.scheduler = scheduler
        self.queue = queue
        self.authenticator = authenticator
        self.calendar_api = calendar_api or GoogleCalendarAPI(GoogleCalendarService())
        self.gmail_api = gmail_api or GmailAPI(GmailService())

    @staticmethod
    def _error(status: int, message: str) -> APIResponse:
        return APIResponse(status, {"ok": False, "error": message})

    def _authorize(
        self,
        headers: Mapping[str, str] | None,
    ) -> APIResponse | None:
        if self.authenticator is None:
            return None
        decision = self.authenticator.authenticate(headers)
        if decision.allowed:
            return None
        return self._error(401, decision.reason)

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> APIResponse:
        verb = method.strip().upper()
        parsed = urlsplit(path)
        route = "/" + parsed.path.strip("/")
        query = {
            key: values[-1]
            for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
        }

        try:
            if verb == "GET" and route == "/v1/status":
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "service": "ZeusEXai Mobile API",
                        "network_listener": False,
                    },
                )

            blocked = self._authorize(headers)
            if blocked is not None:
                return blocked

            if route == "/v1/integrations/google-calendar/status" and verb == "GET":
                response = self.calendar_api.dispatch(verb, route)
                return APIResponse(response.status, response.body)

            if route == "/v1/integrations/google-calendar/events" and verb == "GET":
                response = self.calendar_api.dispatch(verb, route, query=query)
                return APIResponse(response.status, response.body)

            if (
                route == "/v1/integrations/google-calendar/events/preview"
                and verb == "POST"
            ):
                response = self.calendar_api.dispatch(verb, route, body)
                return APIResponse(response.status, response.body)

            if route == "/v1/integrations/gmail/status" and verb == "GET":
                response = self.gmail_api.dispatch(verb, route)
                return APIResponse(response.status, response.body)

            if route == "/v1/integrations/gmail/messages" and verb == "GET":
                response = self.gmail_api.dispatch(verb, route, query=query)
                return APIResponse(response.status, response.body)

            if route == "/v1/integrations/gmail/drafts/preview" and verb == "POST":
                response = self.gmail_api.dispatch(verb, route, body)
                return APIResponse(response.status, response.body)

            if verb == "GET" and route == "/v1/reports":
                reports = self.reports.list()
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "items": [
                            {
                                "id": item.id,
                                "product_name": item.product_name,
                                "marketplace": item.marketplace,
                                "profit": str(item.profit),
                                "margin_percent": str(item.margin_percent),
                                "potential_score": (
                                    str(item.potential_score)
                                    if item.potential_score is not None
                                    else None
                                ),
                            }
                            for item in reports
                        ],
                    },
                )

            if verb == "GET" and route.startswith("/v1/reports/"):
                report_id = int(route.rsplit("/", 1)[-1])
                report = self.reports.get(report_id)
                if report is None:
                    return self._error(404, "Relatório não encontrado.")
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "report": report.report,
                        "markdown": report.markdown,
                    },
                )

            if verb == "GET" and route == "/v1/campaign-templates":
                templates = self.templates.list()
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "items": [
                            {"id": item.id, **asdict(item.template)}
                            for item in templates
                        ],
                    },
                )

            if verb == "GET" and route == "/v1/schedules":
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "items": [asdict(task) for task in self.scheduler.list()],
                    },
                )

            if verb == "GET" and route == "/v1/queue":
                if self.queue is None:
                    return self._error(503, "Fila comercial não configurada.")
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "items": [asdict(job) for job in self.queue.list()],
                    },
                )

            if verb == "POST" and route == "/v1/analysis360":
                payload = dict(body or {})
                save = bool(payload.pop("save", False))
                report = analysis_360_from_mapping(payload)
                response: dict[str, Any] = {
                    "ok": True,
                    "report": report.to_dict(),
                }
                if save:
                    response["report_id"] = self.reports.save(report).id
                return APIResponse(201 if save else 200, response)

            if verb == "POST" and route == "/v1/campaign":
                package = campaign_from_mapping(dict(body or {}))
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "campaign": package.to_dict(),
                    },
                )

            if verb == "POST" and route == "/v1/achadinhos":
                request, policy, catalog = _achadinhos_request(dict(body or {}))
                analyses = CommercialBatchService().analyze(request)
                campaigns = build_achadinhos_campaigns(
                    analyses,
                    policy=policy,
                    catalog_by_listing=catalog,
                )
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "achadinhos": campaigns.to_dict(),
                    },
                )

            if verb == "POST" and route == "/v1/schedules":
                payload = dict(body or {})
                job_type = str(payload.get("job_type") or "")
                scheduled_text = str(payload.get("scheduled_for") or "")
                task_payload = payload.get("payload") or {}
                if not isinstance(task_payload, Mapping):
                    raise ValueError("payload precisa ser um objeto.")
                task = self.scheduler.schedule(
                    job_type,
                    task_payload,
                    datetime.fromisoformat(scheduled_text),
                )
                return APIResponse(
                    201,
                    {"ok": True, "task": asdict(task)},
                )
        except (TypeError, ValueError, ArithmeticError) as exc:
            return self._error(400, str(exc))

        return self._error(404, "Rota não encontrada.")


__all__ = ["APIResponse", "MobileAPIService"]
