"""Plano seguro e auditável para futura configuração OAuth do Google."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Sequence
from urllib.parse import urlsplit


READ_ONLY_SCOPES = {
    "calendar": "https://www.googleapis.com/auth/calendar.events.readonly",
    "gmail": "https://www.googleapis.com/auth/gmail.readonly",
    "drive": "https://www.googleapis.com/auth/drive.metadata.readonly",
}


@dataclass(frozen=True, slots=True)
class GoogleOAuthSetupPlan:
    integrations: tuple[str, ...]
    scopes: tuple[str, ...]
    callback_url: str
    external_action_performed: bool = False
    requires_user_authorization: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_google_oauth_setup_plan(
    integrations: Sequence[str],
    *,
    callback_url: str = "http://127.0.0.1:8765/oauth/google/callback",
) -> GoogleOAuthSetupPlan:
    """Gera uma prévia sem aceitar client secret, token ou código OAuth."""

    normalized = tuple(
        dict.fromkeys(str(value).strip().lower() for value in integrations)
    )
    if not normalized:
        raise ValueError("Selecione ao menos uma integração Google.")
    unknown = sorted(set(normalized).difference(READ_ONLY_SCOPES))
    if unknown:
        raise ValueError("Integração Google não suportada: " + ", ".join(unknown))

    parsed = urlsplit(callback_url.strip())
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("O callback OAuth precisa usar HTTP no loopback local.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("O callback OAuth não pode conter credenciais ou parâmetros.")

    return GoogleOAuthSetupPlan(
        integrations=normalized,
        scopes=tuple(READ_ONLY_SCOPES[name] for name in normalized),
        callback_url=callback_url.strip(),
    )


__all__ = [
    "GoogleOAuthSetupPlan",
    "READ_ONLY_SCOPES",
    "build_google_oauth_setup_plan",
]
