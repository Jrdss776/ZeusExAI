"""Cliente HTTP somente-leitura e limitado para integrações comerciais."""

from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError
from time import monotonic, sleep
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import json
import re

from openjarvis.zeusex.marketplace_listings import (
    MercadoLivreAdapter,
    NormalizedListing,
    ShopeeAdapter,
)


class MarketplaceHTTPError(RuntimeError):
    """Falha sanitizada de consulta externa."""


class ResponseLike(Protocol):
    status: int

    def read(self, amount: int = -1) -> bytes:
        """Lê bytes da resposta."""

    def __enter__(self) -> "ResponseLike":
        """Abre o contexto da resposta."""

    def __exit__(self, *args: object) -> None:
        """Fecha o contexto da resposta."""


Transport = Callable[[Request, float], ResponseLike]


@dataclass(frozen=True, slots=True)
class HTTPClientConfig:
    allowed_hosts: tuple[str, ...]
    timeout_seconds: float = 10.0
    retries: int = 2
    minimum_interval_seconds: float = 0.25
    maximum_response_bytes: int = 2_000_000

    def __post_init__(self) -> None:
        hosts = tuple(host.strip().lower() for host in self.allowed_hosts if host.strip())
        if not hosts:
            raise ValueError("Informe ao menos um host permitido.")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 30:
            raise ValueError("O timeout precisa estar entre 0 e 30 segundos.")
        if not 0 <= self.retries <= 5:
            raise ValueError("O número de repetições precisa estar entre 0 e 5.")
        if self.minimum_interval_seconds < 0:
            raise ValueError("O intervalo mínimo não pode ser negativo.")
        if self.maximum_response_bytes < 1 or self.maximum_response_bytes > 10_000_000:
            raise ValueError("O limite de resposta precisa estar entre 1 e 10000000 bytes.")
        object.__setattr__(self, "allowed_hosts", hosts)


def _default_transport(request: Request, timeout: float) -> ResponseLike:
    return urlopen(request, timeout=timeout)  # type: ignore[return-value]


class ReadOnlyHTTPClient:
    """Executa exclusivamente GET em hosts HTTPS previamente autorizados."""

    def __init__(
        self,
        config: HTTPClientConfig,
        *,
        transport: Transport = _default_transport,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.config = config
        self.transport = transport
        self.clock = clock
        self.sleeper = sleeper
        self._last_request_at: float | None = None

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("A integração aceita somente URLs HTTPS.")
        if parsed.username or parsed.password:
            raise ValueError("Credenciais não podem fazer parte da URL.")
        host = (parsed.hostname or "").lower()
        if host not in self.config.allowed_hosts:
            raise ValueError(f"Host não autorizado: {host or 'ausente'}.")
        if parsed.port not in {None, 443}:
            raise ValueError("Somente a porta HTTPS padrão é permitida.")

    def _respect_rate_limit(self) -> None:
        if self._last_request_at is None:
            return
        remaining = self.config.minimum_interval_seconds - (self.clock() - self._last_request_at)
        if remaining > 0:
            self.sleeper(remaining)

    def get_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        self._validate_url(url)
        safe_headers = {"Accept": "application/json", "User-Agent": "ZeusEXai/1.0"}
        for key, value in (headers or {}).items():
            if key.lower() in {"host", "content-length"}:
                raise ValueError(f"Cabeçalho controlado não permitido: {key}.")
            safe_headers[str(key)] = str(value)

        last_error = "Falha de rede."
        for attempt in range(self.config.retries + 1):
            self._respect_rate_limit()
            request = Request(url, headers=safe_headers, method="GET")
            self._last_request_at = self.clock()
            try:
                with self.transport(request, self.config.timeout_seconds) as response:
                    payload = response.read(self.config.maximum_response_bytes + 1)
                    if len(payload) > self.config.maximum_response_bytes:
                        raise MarketplaceHTTPError("A resposta excedeu o limite permitido.")
                    decoded = json.loads(payload.decode("utf-8"))
                    if not isinstance(decoded, dict):
                        raise MarketplaceHTTPError("A resposta precisa ser um objeto JSON.")
                    return decoded
            except HTTPError as exc:
                last_error = f"Serviço respondeu HTTP {exc.code}."
                retryable = exc.code == 429 or 500 <= exc.code < 600
                if not retryable or attempt >= self.config.retries:
                    break
            except (URLError, TimeoutError):
                last_error = "Serviço indisponível ou tempo limite excedido."
                if attempt >= self.config.retries:
                    break
            except (UnicodeDecodeError, JSONDecodeError):
                raise MarketplaceHTTPError("O serviço retornou JSON inválido.") from None
            if attempt < self.config.retries:
                self.sleeper(min(0.5 * (2**attempt), 4.0))
        raise MarketplaceHTTPError(last_error)


@dataclass(frozen=True, slots=True)
class MercadoLivreReadClient:
    http: ReadOnlyHTTPClient
    adapter: MercadoLivreAdapter = MercadoLivreAdapter()

    @classmethod
    def create(cls) -> "MercadoLivreReadClient":
        config = HTTPClientConfig(allowed_hosts=("api.mercadolibre.com",))
        return cls(ReadOnlyHTTPClient(config))

    def fetch_listing(self, listing_id: str) -> NormalizedListing:
        clean_id = listing_id.strip().upper()
        if not re.fullmatch(r"[A-Z]{3,4}-?\d+", clean_id):
            raise ValueError("Identificador do Mercado Livre inválido.")
        payload = self.http.get_json(
            f"https://api.mercadolibre.com/items/{quote(clean_id, safe='')}"
        )
        return self.adapter.normalize(payload)


@dataclass(frozen=True, slots=True)
class ShopeeReadClient:
    """Consulta um endpoint Shopee configurado; nenhum endpoint é presumido."""

    http: ReadOnlyHTTPClient
    endpoint_template: str
    adapter: ShopeeAdapter = ShopeeAdapter()

    def __post_init__(self) -> None:
        if "{item_id}" not in self.endpoint_template:
            raise ValueError("O endpoint Shopee precisa conter {item_id}.")
        self.http._validate_url(self.endpoint_template.replace("{item_id}", "1"))

    def fetch_listing(
        self,
        item_id: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> NormalizedListing:
        clean_id = item_id.strip()
        if not clean_id.isdigit():
            raise ValueError("Identificador Shopee inválido.")
        url = self.endpoint_template.replace("{item_id}", quote(clean_id, safe=""))
        return self.adapter.normalize(self.http.get_json(url, headers=headers))


__all__ = [
    "HTTPClientConfig",
    "MarketplaceHTTPError",
    "MercadoLivreReadClient",
    "ReadOnlyHTTPClient",
    "ShopeeReadClient",
]
