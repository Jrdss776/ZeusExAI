"""Servidor HTTP local opt-in para a futura interface Android."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from typing import Any
import json

from openjarvis.zeusex.mobile_api import APIResponse, MobileAPIService
from openjarvis.zeusex.pwa_assets import (
    PWA_ICON_SVG,
    PWA_MANIFEST_JSON,
    PWA_SERVICE_WORKER,
)

DASHBOARD_HTML = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="dark">
  <meta name="theme-color" content="#0d2038">
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" href="/icon.svg" type="image/svg+xml">
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
    <h2>Achadinhos do JR</h2>
    <p class="muted">Analisa um lote, ranqueia oportunidades e gera campanhas apenas para os itens aprovados.</p>
    <label for="achadinhos-payload">Lote comercial e política de seleção em JSON</label>
    <textarea id="achadinhos-payload">{
  "marketplace": "shopee",
  "payload": {
    "items": [
      {"item_id": 10, "name": "Produto de exemplo", "price": "79.90"}
    ]
  },
  "costs_by_listing": {
    "10": {
      "product_cost": "35",
      "marketplace_fee_percent": "12",
      "tax_percent": "4"
    }
  },
  "signals_by_listing": {
    "10": {
      "demand": "80",
      "competition": "30",
      "margin": "65",
      "listing_quality": "75"
    }
  },
  "competitors_by_listing": {
    "10": [
      {"item_id": 11, "name": "Concorrente", "price": "82.90"}
    ]
  },
  "policy": {
    "minimum_score": "50",
    "allowed_classifications": ["alto", "moderado"],
    "target_margin_percent": "20"
  }
}</textarea>
    <div class="actions">
      <button data-action="achadinhos">Gerar Achadinhos aprovados</button>
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
    <h2>Central Google</h2>
    <p class="muted">Diagnóstico sanitizado de Calendar, Gmail e Drive.</p>
    <div class="actions">
      <button data-action="googleStatus">Verificar integrações</button>
    </div>
  </section>
  <section>
    <h2>Google Calendar</h2>
    <p class="muted">Integração opcional. A prévia é local e nunca cria o evento.</p>
    <label for="calendar-payload">Evento para revisão em JSON</label>
    <textarea id="calendar-payload">{
  "title": "Planejamento ZeusExAI",
  "start": "2026-07-22T09:00:00-03:00",
  "end": "2026-07-22T10:00:00-03:00",
  "location": "Online"
}</textarea>
    <div class="actions">
      <button data-action="calendarStatus">Status do calendário</button>
      <button data-action="calendarEvents">Próximos 7 dias</button>
      <button data-action="calendarPreview">Revisar prévia local</button>
    </div>
  </section>
  <section>
    <h2>Gmail</h2>
    <p class="muted">Triagem opcional e prévia local. O painel não envia mensagens.</p>
    <label for="gmail-payload">Resposta para revisão em JSON</label>
    <textarea id="gmail-payload">{
  "recipients": ["cliente@example.com"],
  "subject": "Resposta do ZeusExAI",
  "body": "Revise esta mensagem antes de qualquer envio externo."
}</textarea>
    <div class="actions">
      <button data-action="gmailStatus">Status do Gmail</button>
      <button data-action="gmailUnread">Mensagens não lidas</button>
      <button data-action="gmailPreview">Revisar resposta local</button>
    </div>
  </section>
  <section>
    <h2>Google Drive</h2>
    <p class="muted">Pesquisa somente metadados. O painel não baixa, envia, altera ou exclui arquivos.</p>
    <label for="drive-query">Nome ou termo para pesquisa</label>
    <input id="drive-query" type="search" maxlength="500" placeholder="Ex.: relatório de vendas">
    <div class="actions">
      <button data-action="driveStatus">Status do Drive</button>
      <button data-action="driveSearch">Pesquisar metadados</button>
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
    analysis: ["POST", "/v1/analysis360", "payload"],
    campaign: ["POST", "/v1/campaign", "payload"],
    achadinhos: ["POST", "/v1/achadinhos", "achadinhos-payload"],
    reports: ["GET", "/v1/reports", null],
    schedules: ["GET", "/v1/schedules", null],
    queue: ["GET", "/v1/queue", null],
    templates: ["GET", "/v1/campaign-templates", null],
    googleStatus: ["GET", "/v1/integrations/google/status", null],
    calendarStatus: ["GET", "/v1/integrations/google-calendar/status", null],
    calendarEvents: ["GET", "/v1/integrations/google-calendar/events", null],
    calendarPreview: ["POST", "/v1/integrations/google-calendar/events/preview", "calendar-payload"],
    gmailStatus: ["GET", "/v1/integrations/gmail/status", null],
    gmailUnread: ["GET", "/v1/integrations/gmail/messages?q=is%3Aunread", null],
    gmailPreview: ["POST", "/v1/integrations/gmail/drafts/preview", "gmail-payload"],
    driveStatus: ["GET", "/v1/integrations/google-drive/status", null],
    driveSearch: ["GET", "/v1/integrations/google-drive/files", null]
  };

  async function callAPI(action) {
    const route = routes[action];
    const token = document.getElementById("token").value;
    let url = route[1];
    if (action === "calendarEvents") {
      const start = new Date();
      const end = new Date(start.getTime() + 7 * 24 * 60 * 60 * 1000);
      url += "?time_min=" + encodeURIComponent(start.toISOString());
      url += "&time_max=" + encodeURIComponent(end.toISOString());
    }
    if (action === "driveSearch") {
      const query = document.getElementById("drive-query").value.trim();
      if (query) url += "?q=" + encodeURIComponent(query);
    }
    const options = {
      method: route[0],
      headers: {Authorization: "Bearer " + token}
    };
    if (route[0] === "POST") {
      let payload;
      try {
        payload = JSON.parse(document.getElementById(route[2]).value);
      } catch (error) {
        result.textContent = "JSON inválido.";
        return;
      }
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(payload);
    }
    result.textContent = "Processando localmente...";
    try {
      const response = await fetch(url, options);
      result.textContent = JSON.stringify(await response.json(), null, 2);
    } catch (error) {
      result.textContent = "Falha local: " + error.name;
    }
  }

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => callAPI(button.dataset.action));
  });
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
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

        def _send_static(
            self,
            content: str,
            content_type: str,
            *,
            cache_control: str = "no-store",
        ) -> None:
            payload = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", cache_control)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            if self.path == "/manifest.webmanifest":
                self._send_static(
                    PWA_MANIFEST_JSON,
                    "application/manifest+json; charset=utf-8",
                )
                return
            if self.path == "/icon.svg":
                self._send_static(
                    PWA_ICON_SVG,
                    "image/svg+xml; charset=utf-8",
                    cache_control="public, max-age=86400",
                )
                return
            if self.path == "/sw.js":
                self._send_static(
                    PWA_SERVICE_WORKER,
                    "text/javascript; charset=utf-8",
                )
                return
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
            self._send_json(
                APIResponse(405, {"ok": False, "error": "Método não permitido."})
            )

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
