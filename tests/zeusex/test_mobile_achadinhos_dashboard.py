"""Testes do formulário Achadinhos do JR no painel local."""

from openjarvis.zeusex.mobile_server import DASHBOARD_HTML


def test_dashboard_exposes_dedicated_achadinhos_form() -> None:
    assert "Achadinhos do JR" in DASHBOARD_HTML
    assert 'id="achadinhos-payload"' in DASHBOARD_HTML
    assert 'data-action="achadinhos"' in DASHBOARD_HTML
    assert 'achadinhos: ["POST", "/v1/achadinhos", "achadinhos-payload"]' in DASHBOARD_HTML


def test_dashboard_keeps_achadinhos_data_local_and_ephemeral() -> None:
    assert "nenhuma ação publica anúncios" in DASHBOARD_HTML
    assert "localStorage" not in DASHBOARD_HTML
    assert "sessionStorage" not in DASHBOARD_HTML
    assert "Processando localmente" in DASHBOARD_HTML


def test_each_post_action_uses_its_declared_textarea() -> None:
    assert "document.getElementById(route[2]).value" in DASHBOARD_HTML
    assert 'analysis: ["POST", "/v1/analysis360", "payload"]' in DASHBOARD_HTML
    assert 'campaign: ["POST", "/v1/campaign", "payload"]' in DASHBOARD_HTML
