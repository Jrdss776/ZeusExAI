"""Plano OAuth Google com privilégio mínimo."""

import pytest

from openjarvis.zeusex.google_setup import build_google_oauth_setup_plan
from openjarvis.zeusex.google_setup_api import GoogleSetupAPI


def test_google_setup_uses_read_only_scopes() -> None:
    plan = build_google_oauth_setup_plan(["calendar", "gmail", "drive"])
    assert len(plan.scopes) == 3
    assert all("readonly" in scope for scope in plan.scopes)
    assert plan.external_action_performed is False
    assert plan.requires_user_authorization is True


def test_google_setup_deduplicates_integrations() -> None:
    plan = build_google_oauth_setup_plan(["gmail", "GMAIL", "drive"])
    assert plan.integrations == ("gmail", "drive")


def test_google_setup_rejects_non_loopback_callback() -> None:
    with pytest.raises(ValueError, match="loopback"):
        build_google_oauth_setup_plan(
            ["drive"], callback_url="https://example.com/oauth/callback"
        )


def test_google_setup_rejects_unknown_integration() -> None:
    with pytest.raises(ValueError, match="não suportada"):
        build_google_oauth_setup_plan(["youtube"])


def test_google_setup_api_only_previews() -> None:
    api = GoogleSetupAPI()
    preview = api.dispatch(
        "POST",
        "/v1/integrations/google/setup/preview",
        {"integrations": ["gmail"]},
    )
    blocked = api.dispatch("POST", "/v1/integrations/google/setup/connect", {})
    assert preview.status == 200
    assert preview.body["plan"]["external_action_performed"] is False
    assert blocked.status == 404
