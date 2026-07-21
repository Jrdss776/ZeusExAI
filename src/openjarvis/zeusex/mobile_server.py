"""Servidor HTTP local opt-in para a futura interface Android."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from typing import Any
import json

from openjarvis.zeusex.mobile_api import APIResponse, MobileAPIService

DASHBOARD_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>ZeusEXai Mobile</title>
  <style>
    :root { font-family: system-ui, sans-serif; color: #eef5ff; background: #07111f; }
    body { margin: 0; padding: 24px; max-width: 780px; margin-inline: auto; }
    header, section { background: #0d2038; border: 1px solid #25486d; border-radius: 16px; padding: 20px; margin-bottom: 16px; }
    h1 { color: #f2c14e; margin-top: 0; }
    label { display: block; margin-bottom: 6px; }
    input, button { box-sizing: border-box; border-radius: 10px; padding: 12px; font: inherit; }
    input { width: 100%; color: #eef5ff; background: #07111f; border: 1px solid #3c648d; }
    button { margin-top: 10px; color: #07111f; background: #f2c14e; border: 0; font-weight: 700; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; color: #b9d8f5; }
    .safe { color: #8ce99a; }
  </style>
</head>
<body>
  <header>
    <h1>ZeusEXai Mobile</h1>
    <p class="safe">Servidor local: este painel funciona somente no próprio aparelho.</p>
  </header>
  <section>
    <label for="token">Token local (não é salvo no navegador)</label>
    <input id="token" type="password" autocomplete="off">
    <button id="load">Carregar relatórios</button>
  </section>
  <section>
    <h2>Resposta</h2>
    <pre id="result">Pronto.</pre>
  </section>
<script>
  const result = document.getElementById("result");
  document.getElementById("load").addEventListener("click", async () => {
    const token = document.getElementById("token").value;
    try {
      const response = await fetch("/v1/reports", {
        headers: {Authorization: "Bearer " + token}
      });
      result.textContent = JSON.stringify(await response.json(), null, 2);
    } catch (error) {
      result.textContent = "Falha local: " + error.name;
    }
  });
</script>
</body>
</html>
"""


@dataclass(frozen=True, slots=True)
class MobileServerConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    maximum_request_bytes: int = 1_000_000

    def __post_init__(self) -> None:
        try:
            address = ip_address(self.host)
        except ValueError as exc:
            raise ValueError("Informe um endereço IP de loopback válido.") from exc
        if not address.is_loopback:
            raise ValueError("O servidor móvel só pode usar um endereço de loopback.")
        if self.port != 0 and not 1024 <= self.port <= 65535:
            raise ValueError("A porta precisa estar entre 1024 e 65535.")
        if not 1 <= self.maximum_request_bytes <= 2_000_000:
            raise ValueError("O limite da requisição precisa estar entre 1 e 2000000 bytes.")


class LocalMobileHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


def _handler(service: MobileAPIService, config: MobileServerConfig):
    class MobileHandler(BaseHTTPRequestHandler):
        server_version = "ZeusEXaiLocal/1.0"

        def log_message(self, format: str, *args: object) -> None:
            del format, args

        def _send_json(self, response: APIResponse) -> None:
            payload = json.dumps(
                response.body,
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def _headers(self) -> dict[str, str]:
            authorization = self.headers.get("Authorization")
            return {"Authorization": authorization} if authorization else {}

        def _read_json(self) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("Content-Length inválido.") from exc
            if length < 0 or length > config.maximum_request_bytes:
                raise ValueError("Corpo da requisição excede o limite permitido.")
            if length == 0:
                return {}
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("O corpo precisa ser um objeto JSON.")
            return payload

        def do_GET(self) -> None:
            if self.path == "/":
                payload = DASHBOARD_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'",
                )
                self.end_headers()
                self.wfile.write(payload)
                return
            response = service.dispatch(
                "GET",
                self.path,
                headers=self._headers(),
            )
            self._send_json(response)

        def do_POST(self) -> None:
            try:
                body = self._read_json()
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                self._send_json(APIResponse(400, {"ok": False, "error": str(exc)}))
                return
            response = service.dispatch(
                "POST",
                self.path,
                body,
                headers=self._headers(),
            )
            self._send_json(response)

        def do_PUT(self) -> None:
            self._send_json(APIResponse(405, {"ok": False, "error": "Método não permitido."}))

        do_DELETE = do_PUT
        do_PATCH = do_PUT

    return MobileHandler


def create_mobile_server(
    service: MobileAPIService,
    config: MobileServerConfig | None = None,
) -> LocalMobileHTTPServer:
    settings = config or MobileServerConfig()
    return LocalMobileHTTPServer(
        (settings.host, settings.port),
        _handler(service, settings),
    )


def serve_mobile_api(
    service: MobileAPIService,
    config: MobileServerConfig | None = None,
) -> None:
    server = create_mobile_server(service, config)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()


__all__ = [
    "DASHBOARD_HTML",
    "LocalMobileHTTPServer",
    "MobileServerConfig",
    "create_mobile_server",
    "serve_mobile_api",
]
