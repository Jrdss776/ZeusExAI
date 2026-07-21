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
    body { margin: 0; padding: 20px; max-width: 900px; margin-inline: auto; }
    header, section { background: #0d2038; border: 1px solid #25486d; border-radius: 16px; padding: 18px; margin-bottom: 14px; }
    h1 { color: #f2c14e; margin-top: 0; }
    h2 { margin-top: 0; }
    label { display: block; margin: 8px 0 6px; }
    input, textarea, button { box-sizing: border-box; border-radius: 10px; padding: 11px; font: inherit; }
    input, textarea { width: 100%; color: #eef5ff; background: #07111f; border: 1px solid #3c648d; }
    textarea { min-height: 220px; resize: vertical; }
    button { color: #07111f; background: #f2c14e; border: 0; font-weight: 700; cursor: pointer; }
    .actions { display: grid; grid-template-columns: repeat(auto-fit,minmax(150px,1fr)); gap: 8px; margin-top: 12px; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; color: #b9d8f5; max-height: 55vh; overflow: auto; }
    .safe { color: #8ce99a; }
    .muted { color: #9fb5cc; }
  </style>
</head>
<body>
  <header>
    <h1>ZeusEXai Mobile</h1>
    <p class="safe">Painel local e autenticado — nenhuma ação publica anúncios.</p>
  </header>
  <section>
    <h2>Acesso</h2>
    <label for="token">Token local (não é salvo no navegador)</label>
    <input id="token" type="password" autocomplete="off">
  </section>
  <section>
    <h2>Dados comerciais</h2>
    <label for="payload">Produto, atributos, sinais, concorrentes e catálogo em JSON</label>
    <textarea id="payload">{
  "save": true,
  "product": {
    "name": "Produto de exemplo",
    "marketplace": "shopee",
    "sale_price": "49.90",
    "product_cost": "25"
  },
  "attributes": {
    "Material": "informe o material"
  }
}</textarea>
    <div class="actions">
      <button data-action="analysis">Criar Análise 360</button>
      <button data-action="campaign">Gerar campanha</button>
    </div>
  </section>
  <section>
    <h2>Acompanhamento</h2>
    <div class="actions">
      <button data-action="reports">Relatórios</button>
      <button data-action="schedules">Agenda</button>
      <button data-action="queue">Fila comercial</button>
      <button data-action="templates">Modelos</button>
    </div>
  </section>
  <section>
    <h2>Resposta</h2>
    <p class="muted">Os dados abaixo permanecem neste aparelho.</p>
    <pre id="result">Pronto.</pre>
  </section>
<script>
  const result = document.getElementById("result");
  const routes = {
    analysis: ["POST", "/v1/analysis360"],
    campaign: ["POST", "/v1/campaign"],
    reports: ["GET", "/v1/reports"],
    schedules: ["GET", "/v1/schedules"],
    queue: ["GET", "/v1/queue"],
    templates: ["GET", "/v1/campaign-templates"]
  };

  async function callAPI(action) {
    const route = routes[action];
    const token = document.getElementById("token").value;
    const options = {
      method: route[0],
      headers: {Authorization: "Bearer " + token}
    };
    if (route[0] === "POST") {
      let payload;
      try {
        payload = JSON.parse(document.getElementById("payload").value);
      } catch (error) {
        result.textContent = "JSON inválido.";
        return;
      }
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(payload);
    }
    result.textContent = "Processando localmente...";
    try {
      const response = await fetch(route[1], options);
      result.textContent = JSON.stringify(await response.json(), null, 2);
    } catch (error) {
      result.textContent = "Falha local: " + error.name;
    }
  }

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => callAPI(button.dataset.action));
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
