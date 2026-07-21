"""Camada de serviço JSON para a interface Android local."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from openjarvis.zeusex.analysis_360 import analysis_360_from_mapping
from openjarvis.zeusex.analysis_queue import AnalysisQueue
from openjarvis.zeusex.auth import LocalAPIAuthenticator
from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.campaigns import campaign_from_mapping
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


@dataclass(frozen=True, slots=True)
class APIResponse:
    status: int
    body: dict[str, Any]


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
    ) -> None:
        self.reports = reports
        self.templates = templates
        self.scheduler = scheduler
        self.queue = queue
        self.authenticator = authenticator

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
        route = "/" + path.strip("/")

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
