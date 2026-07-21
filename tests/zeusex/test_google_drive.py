import pytest

from openjarvis.zeusex.google_drive import (
    DriveAccessMode,
    DriveConnectorStatus,
    DriveFile,
    GoogleDriveConfig,
    GoogleDriveService,
)
from openjarvis.zeusex.google_drive_api import GoogleDriveAPI


class FakeDriveConnector:
    def status(self):
        return DriveConnectorStatus(True, "metadata_read", True)

    def list_files(self, *, query, max_results):
        return [DriveFile("file-1", query or "Relatório", "application/pdf", size=42)]

    def get_file(self, file_id):
        return DriveFile(file_id, "Relatório", "application/pdf", size=42)


def test_drive_is_disabled_by_default() -> None:
    service = GoogleDriveService()
    assert service.status().enabled is False
    with pytest.raises(PermissionError):
        service.list_files()


def test_metadata_mode_lists_and_limits_files() -> None:
    service = GoogleDriveService(
        FakeDriveConnector(),
        GoogleDriveConfig(True, DriveAccessMode.METADATA_READ, max_results=5),
    )
    files = service.list_files(query="  vendas  ", limit=99)
    assert files[0].name == "vendas"
    assert files[0].size == 42


def test_file_id_is_validated_before_connector_call() -> None:
    service = GoogleDriveService(
        FakeDriveConnector(),
        GoogleDriveConfig(True, DriveAccessMode.METADATA_READ),
    )
    with pytest.raises(ValueError, match="inválido"):
        service.get_file("id com espaço")


def test_api_is_strictly_read_only() -> None:
    api = GoogleDriveAPI(
        GoogleDriveService(
            FakeDriveConnector(),
            GoogleDriveConfig(True, DriveAccessMode.METADATA_READ),
        )
    )
    listed = api.dispatch("GET", "/v1/integrations/google-drive/files", query={"q": "SEO"})
    metadata = api.dispatch("GET", "/v1/integrations/google-drive/files/file-1")
    blocked = api.dispatch("POST", "/v1/integrations/google-drive/files")

    assert listed.status == 200
    assert listed.body["items"][0]["name"] == "SEO"
    assert metadata.status == 200
    assert blocked.status == 404


def test_drive_file_rejects_negative_size() -> None:
    with pytest.raises(ValueError, match="negativo"):
        DriveFile("1", "Arquivo", "text/plain", size=-1)
