"""Autenticação local em memória para a futura API Android."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from hmac import compare_digest
from typing import Mapping


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    allowed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class LocalAPIAuthenticator:
    """Mantém somente o hash do token durante a execução."""

    token_hash: str

    @classmethod
    def from_secret(cls, secret: str) -> "LocalAPIAuthenticator":
        clean_secret = secret.strip()
        if len(clean_secret) < 16:
            raise ValueError("O token local precisa ter pelo menos 16 caracteres.")
        return cls(sha256(clean_secret.encode("utf-8")).hexdigest())

    def authenticate(
        self,
        headers: Mapping[str, str] | None,
    ) -> AuthenticationResult:
        authorization = ""
        for key, value in (headers or {}).items():
            if key.lower() == "authorization":
                authorization = str(value).strip()
                break
        scheme, separator, token = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not token.strip():
            return AuthenticationResult(False, "Token Bearer obrigatório.")
        candidate = sha256(token.strip().encode("utf-8")).hexdigest()
        if not compare_digest(candidate, self.token_hash):
            return AuthenticationResult(False, "Token local inválido.")
        return AuthenticationResult(True, "Autenticado.")


__all__ = ["AuthenticationResult", "LocalAPIAuthenticator"]
