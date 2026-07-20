"""Testes do cliente HTTP comercial somente-leitura."""

from io import BytesIO
from urllib.error import HTTPError

import pytest

from openjarvis.zeusex.marketplace_http import (
    HTTPClientConfig,
    MarketplaceHTTPError,
    MercadoLivreReadClient,
    ReadOnlyHTTPClient,
)


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = BytesIO(payload)
        self.status = 200

    def read(self, amount: int = -1) -> bytes:
        return self.payload.read(amount)

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        return None


def test_client_accepts_only_allowed_https_host() -> None:
    client = ReadOnlyHTTPClient(
        HTTPClientConfig(("api.example.com",), minimum_interval_seconds=0),
        transport=lambda request, timeout: FakeResponse(b'{"ok": true}'),
    )

    assert client.get_json("https://api.example.com/item") == {"ok": True}
    with pytest.raises(ValueError, match="HTTPS"):
        client.get_json("http://api.example.com/item")
    with pytest.raises(ValueError, match="não autorizado"):
        client.get_json("https://internal.example/item")


def test_client_retries_retryable_status() -> None:
    calls = []

    def transport(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 503, "unavailable", {}, None)
        return FakeResponse(b'{"id": "MLB1"}')

    client = ReadOnlyHTTPClient(
        HTTPClientConfig(("api.example.com",), retries=1, minimum_interval_seconds=0),
        transport=transport,
        sleeper=lambda value: None,
    )

    assert client.get_json("https://api.example.com/item") == {"id": "MLB1"}
    assert len(calls) == 2


def test_client_limits_response_size() -> None:
    client = ReadOnlyHTTPClient(
        HTTPClientConfig(
            ("api.example.com",),
            maximum_response_bytes=5,
            minimum_interval_seconds=0,
        ),
        transport=lambda request, timeout: FakeResponse(b'{"large": true}'),
    )

    with pytest.raises(MarketplaceHTTPError, match="limite"):
        client.get_json("https://api.example.com/item")


def test_mercado_livre_client_validates_id_and_normalizes() -> None:
    http = ReadOnlyHTTPClient(
        HTTPClientConfig(("api.mercadolibre.com",), minimum_interval_seconds=0),
        transport=lambda request, timeout: FakeResponse(
            b'{"id":"MLB123","title":"Produto","price":49.9}'
        ),
    )
    listing = MercadoLivreReadClient(http).fetch_listing("MLB123")

    assert listing.listing_id == "MLB123"
    assert str(listing.price) == "49.90"
