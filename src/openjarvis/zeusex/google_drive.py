"""Fundação opcional e somente-leitura para Google Drive."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol, Sequence


class DriveAccessMode(str, Enum):
    DISABLED = "disabled"
    METADATA_READ = "metadata_read"


@dataclass(frozen=True, slots=True)
class DriveConnectorStatus:
    enabled: bool
    access_mode: str
    authenticated: bool = False
    provider: str = "google_drive"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    modified_at: str = ""
    size: int | None = None
    web_url: str = ""
    owners: tuple[str, ...] = ()
    parent_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip() or not self.mime_type.strip():
            raise ValueError("Arquivo exige id, nome e mime_type.")
        if self.size is not None and self.size < 0:
            raise ValueError("size não pode ser negativo.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GoogleDriveConfig:
    enabled: bool = False
    access_mode: DriveAccessMode = DriveAccessMode.DISABLED
    max_results: int = 50

    def __post_init__(self) -> None:
        if self.enabled and self.access_mode is DriveAccessMode.DISABLED:
            raise ValueError("Google Drive habilitado exige modo metadata_read.")
        if not 1 <= self.max_results <= 100:
            raise ValueError("max_results precisa estar entre 1 e 100.")


class GoogleDriveConnector(Protocol):
    def status(self) -> DriveConnectorStatus:
        """Retorna estado sem credenciais."""

    def list_files(self, *, query: str | None, max_results: int) -> Sequence[DriveFile]:
        """Lista somente metadados."""

    def get_file(self, file_id: str) -> DriveFile | None:
        """Consulta metadados de um arquivo conhecido."""


class DisabledGoogleDriveConnector:
    def status(self) -> DriveConnectorStatus:
        return DriveConnectorStatus(
            enabled=False,
            access_mode=DriveAccessMode.DISABLED.value,
            reason="Google Drive não configurado.",
        )

    def list_files(self, **_: Any) -> Sequence[DriveFile]:
        raise RuntimeError("Google Drive não configurado.")

    def get_file(self, file_id: str) -> DriveFile | None:
        del file_id
        raise RuntimeError("Google Drive não configurado.")


class GoogleDriveService:
    """Aplica política somente-leitura sobre um conector fornecido externamente."""

    def __init__(
        self,
        connector: GoogleDriveConnector | None = None,
        config: GoogleDriveConfig | None = None,
    ) -> None:
        self.connector = connector or DisabledGoogleDriveConnector()
        self.config = config or GoogleDriveConfig()

    def status(self) -> DriveConnectorStatus:
        connector_status = self.connector.status()
        if not self.config.enabled:
            return DriveConnectorStatus(
                enabled=False,
                access_mode=DriveAccessMode.DISABLED.value,
                authenticated=connector_status.authenticated,
                reason="Integração desativada na configuração local.",
            )
        return connector_status

    def _require_read(self) -> None:
        if not self.config.enabled:
            raise PermissionError("Integração com Google Drive está desativada.")
        if self.config.access_mode is not DriveAccessMode.METADATA_READ:
            raise PermissionError("Leitura de metadados do Google Drive não autorizada.")

    def list_files(self, *, query: str | None = None, limit: int | None = None) -> list[DriveFile]:
        self._require_read()
        clean_query = query.strip() if query and query.strip() else None
        if clean_query and len(clean_query) > 500:
            raise ValueError("A consulta do Drive não pode exceder 500 caracteres.")
        bounded = min(max(1, limit or self.config.max_results), self.config.max_results)
        return list(self.connector.list_files(query=clean_query, max_results=bounded))[:bounded]

    def get_file(self, file_id: str) -> DriveFile | None:
        self._require_read()
        clean_id = file_id.strip()
        if not clean_id or len(clean_id) > 200 or any(char.isspace() for char in clean_id):
            raise ValueError("Identificador de arquivo inválido.")
        return self.connector.get_file(clean_id)


__all__ = [
    "DisabledGoogleDriveConnector",
    "DriveAccessMode",
    "DriveConnectorStatus",
    "DriveFile",
    "GoogleDriveConfig",
    "GoogleDriveConnector",
    "GoogleDriveService",
]
