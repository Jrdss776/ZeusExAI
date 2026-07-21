"""Camada de serviço JSON para uma futura interface Android local."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from openjarvis.zeusex.analysis_360 import analysis_360_from_mapping
from openjarvis.zeusex.campaign_store import CampaignTemplateStore
from openjarvis.zeusex.report_store import AnalysisReportStore
from openjarvis.zeusex.scheduler import SafeScheduler


@dataclass(frozen=True, slots=True)
class APIResponse:
    status: int
    body: dict[str, Any]


class MobileAPIService:
    """Despacha operações locais sem abrir porta de rede."""

    def __init__(
        self,
        reports: AnalysisReportStore,
        templates: CampaignTemplateStore,
        scheduler: SafeScheduler,
    ) -> None:
        self.reports = reports
        self.templates = templates
        self.scheduler = scheduler

    @staticmethod
    def _error(status: int, message: str) -> APIResponse:
        return APIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
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

            if verb == "GET" and route == "/v1/campaign-templates":
                templates = self.templates.list()
                return APIResponse(
                    200,
                    {
                        "ok": True,
                        "items": [
                            {
                                "id": item.id,
                                **asdict(item.template),
                            }
                            for item in templates
                        ],
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

            if verb == "POST" and route == "/v1/schedules":
                payload = dict(body or {})
                job_type = str(payload.get("job_type") or "")
                scheduled_text = str(payload.get("scheduled_for") or "")
                task_payload = payload.get("payload") or {}
                if not isinstance(task_payload, Mapping):
                    raise ValueError("payload precisa ser um objeto.")
                scheduled_for = datetime.fromisoformat(scheduled_text)
                task = self.scheduler.schedule(
                    job_type,
                    task_payload,
                    scheduled_for,
                )
                return APIResponse(
                    201,
                    {
                        "ok": True,
                        "task": asdict(task),
                    },
                )
        except (TypeError, ValueError, ArithmeticError) as exc:
            return self._error(400, str(exc))

        return self._error(404, "Rota não encontrada.")


__all__ = ["APIResponse", "MobileAPIService"]
