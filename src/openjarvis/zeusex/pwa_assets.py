"""Recursos estáticos locais da PWA ZeusEXai."""

from __future__ import annotations

import json

PWA_MANIFEST = {
    "id": "/",
    "name": "ZeusEXai Mobile",
    "short_name": "ZeusEXai",
    "description": "Assistente comercial local para análises e campanhas.",
    "lang": "pt-BR",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#07111f",
    "theme_color": "#0d2038",
    "icons": [
        {
            "src": "/icon.svg",
            "sizes": "any",
            "type": "image/svg+xml",
            "purpose": "any maskable",
        }
    ],
}

PWA_MANIFEST_JSON = json.dumps(
    PWA_MANIFEST,
    ensure_ascii=False,
    separators=(",", ":"),
)

PWA_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="112" fill="#07111f"/>
<path d="M296 44 132 282h105l-22 186 165-248H274z" fill="#f2c14e"/>
<circle cx="256" cy="256" r="226" fill="none" stroke="#25486d" stroke-width="18"/>
</svg>
"""

PWA_SERVICE_WORKER = """const CACHE = "zeusex-shell-v1";
const SHELL = ["/", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (
    event.request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/v1/")
  ) {
    return;
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
"""


__all__ = [
    "PWA_ICON_SVG",
    "PWA_MANIFEST",
    "PWA_MANIFEST_JSON",
    "PWA_SERVICE_WORKER",
]
