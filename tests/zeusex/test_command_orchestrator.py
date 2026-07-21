from openjarvis.zeusex.command_orchestrator import (
    CommandDomain,
    CommandOrchestrator,
)


def test_routes_commercial_analysis_command() -> None:
    decision = CommandOrchestrator().route(
        "Zeus, analise este produto e calcule lucro, margem e ROI."
    )

    assert decision.domain is CommandDomain.COMMERCIAL_ANALYSIS
    assert decision.confidence >= 0.55
    assert "lucro" in decision.matched_terms
    assert decision.requires_confirmation is False


def test_routes_achadinhos_before_generic_campaign() -> None:
    decision = CommandOrchestrator().route(
        "Selecione produtos aprovados para os Achadinhos do JR."
    )

    assert decision.domain is CommandDomain.ACHADINHOS


def test_routes_unknown_command_to_original_assistant() -> None:
    decision = CommandOrchestrator().route("Explique a origem do universo.")

    assert decision.domain is CommandDomain.ASSISTANT
    assert decision.matched_terms == ()


def test_dispatch_calls_registered_handler_with_context() -> None:
    received: dict[str, object] = {}

    def handler(command: str, context: dict[str, object]) -> dict[str, object]:
        received["command"] = command
        received["context"] = context
        return {"ok": True}

    orchestrator = CommandOrchestrator({CommandDomain.CAMPAIGN: handler})
    result = orchestrator.dispatch("Gerar campanha para este produto", {"id": "123"})

    assert result.handled is True
    assert result.output == {"ok": True}
    assert received == {
        "command": "Gerar campanha para este produto",
        "context": {"id": "123"},
    }


def test_sensitive_action_requires_confirmation() -> None:
    decision = CommandOrchestrator().route("Publicar anúncio no marketplace")

    assert decision.domain is CommandDomain.CAMPAIGN
    assert decision.requires_confirmation is True


def test_unregistered_domain_is_not_executed() -> None:
    result = CommandOrchestrator().dispatch("Abra o painel comercial")

    assert result.decision.domain is CommandDomain.DASHBOARD
    assert result.handled is False
    assert result.output is None
