from typing import Any, Mapping

from openjarvis.zeusex.command_integrations import build_mobile_orchestrator
from openjarvis.zeusex.mobile_api import APIResponse


class FakeService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> APIResponse:
        self.calls.append(
            {
                "method": method,
                "path": path,
                "body": body,
                "headers": headers,
            }
        )
        return APIResponse(200, {"ok": True, "path": path})


def test_commercial_command_uses_analysis_route() -> None:
    service = FakeService()
    orchestrator = build_mobile_orchestrator(
        service,
        headers={"Authorization": "Bearer local"},
    )

    result = orchestrator.dispatch(
        "Analise este produto e calcule o ROI",
        {"payload": {"marketplace": "shopee"}},
    )

    assert result.handled is True
    assert result.output == {
        "status": 200,
        "body": {"ok": True, "path": "/v1/analysis360"},
    }
    assert service.calls == [
        {
            "method": "POST",
            "path": "/v1/analysis360",
            "body": {"marketplace": "shopee"},
            "headers": {"Authorization": "Bearer local"},
        }
    ]


def test_agenda_command_reads_local_schedule() -> None:
    service = FakeService()
    orchestrator = build_mobile_orchestrator(service)

    result = orchestrator.dispatch("Mostre minha agenda de hoje")

    assert result.handled is True
    assert service.calls[0]["method"] == "GET"
    assert service.calls[0]["path"] == "/v1/schedules"


def test_general_assistant_command_preserves_jarvis_fallback() -> None:
    service = FakeService()
    orchestrator = build_mobile_orchestrator(service)

    result = orchestrator.dispatch("Conte uma história curta")

    assert result.handled is False
    assert service.calls == []
