"""Testes dos recursos PWA locais."""

import json

from openjarvis.zeusex.pwa_assets import (
    PWA_ICON_SVG,
    PWA_MANIFEST_JSON,
    PWA_SERVICE_WORKER,
)


def test_manifest_is_local_standalone_and_has_icon() -> None:
    manifest = json.loads(PWA_MANIFEST_JSON)

    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["icons"][0]["src"] == "/icon.svg"
    assert manifest["icons"][0]["purpose"] == "any maskable"


def test_service_worker_never_caches_api_routes() -> None:
    assert 'url.pathname.startsWith("/v1/")' in PWA_SERVICE_WORKER
    assert 'event.request.method !== "GET"' in PWA_SERVICE_WORKER
    assert "localStorage" not in PWA_SERVICE_WORKER
    assert "Authorization" not in PWA_SERVICE_WORKER


def test_icon_is_self_contained_svg() -> None:
    assert PWA_ICON_SVG.startswith("<svg")
    assert "http://" not in PWA_ICON_SVG.replace(
        "http://www.w3.org/2000/svg",
        "",
    )
    assert "<script" not in PWA_ICON_SVG
