"""Integração opcional e segura com GitHub para o ZeusExAI."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Protocol, Sequence


class GitHubAccessMode(str, Enum):
    DISABLED = "disabled"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


@dataclass(frozen=True, slots=True)
class GitHubConnectorStatus:
    enabled: bool
    access_mode: str
    authenticated: bool = False
    provider: str = "github"
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GitHubRepository:
    full_name: str
    private: bool
    default_branch: str
    open_issues_count: int = 0
    html_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GitHubIssue:
    number: int
    title: str
    state: str
    author: str = ""
    labels: tuple[str, ...] = ()
    html_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GitHubPullRequest:
    number: int
    title: str
    state: str
    head: str
    base: str
    mergeable: bool | None = None
    html_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GitHubCIStatus:
    ref: str
    state: str
    checks_total: int
    checks_failed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GitHubConfig:
    enabled: bool = False
    access_mode: GitHubAccessMode = GitHubAccessMode.DISABLED
    max_results: int = 50

    def __post_init__(self) -> None:
        if self.enabled and self.access_mode is GitHubAccessMode.DISABLED:
            raise ValueError("GitHub habilitado exige modo read_only ou read_write.")
        if not 1 <= self.max_results <= 100:
            raise ValueError("max_results precisa estar entre 1 e 100.")


class GitHubConnector(Protocol):
    def status(self) -> GitHubConnectorStatus: ...
    def list_repositories(self, *, limit: int) -> Sequence[GitHubRepository]: ...
    def list_issues(self, repository: str, *, state: str, limit: int) -> Sequence[GitHubIssue]: ...
    def list_pull_requests(self, repository: str, *, state: str, limit: int) -> Sequence[GitHubPullRequest]: ...
    def ci_status(self, repository: str, ref: str) -> GitHubCIStatus: ...
    def create_issue(self, repository: str, title: str, body: str) -> GitHubIssue: ...


class DisabledGitHubConnector:
    def status(self) -> GitHubConnectorStatus:
        return GitHubConnectorStatus(False, GitHubAccessMode.DISABLED.value, reason="GitHub não configurado.")

    def __getattr__(self, _: str) -> Any:
        raise RuntimeError("GitHub não configurado.")


class GitHubService:
    """Aplica limites e confirmação sem conhecer token ou SDK GitHub."""

    def __init__(self, connector: GitHubConnector | None = None, config: GitHubConfig | None = None) -> None:
        self.connector = connector or DisabledGitHubConnector()
        self.config = config or GitHubConfig()

    def status(self) -> GitHubConnectorStatus:
        connector_status = self.connector.status()
        if not self.config.enabled:
            return GitHubConnectorStatus(False, GitHubAccessMode.DISABLED.value, connector_status.authenticated, reason="Integração desativada na configuração local.")
        return connector_status

    def _require_read(self) -> None:
        if not self.config.enabled:
            raise PermissionError("Integração com GitHub está desativada.")
        if self.config.access_mode not in {GitHubAccessMode.READ_ONLY, GitHubAccessMode.READ_WRITE}:
            raise PermissionError("Leitura do GitHub não autorizada.")

    def _limit(self, limit: int | None) -> int:
        return min(max(1, limit or self.config.max_results), self.config.max_results)

    @staticmethod
    def _repository(value: str) -> str:
        clean = value.strip()
        if clean.count("/") != 1 or any(not part for part in clean.split("/")):
            raise ValueError("repository precisa usar o formato owner/name.")
        return clean

    def list_repositories(self, *, limit: int | None = None) -> list[GitHubRepository]:
        self._require_read()
        return list(self.connector.list_repositories(limit=self._limit(limit)))

    def list_issues(self, repository: str, *, state: str = "open", limit: int | None = None) -> list[GitHubIssue]:
        self._require_read()
        if state not in {"open", "closed", "all"}:
            raise ValueError("state precisa ser open, closed ou all.")
        return list(self.connector.list_issues(self._repository(repository), state=state, limit=self._limit(limit)))

    def list_pull_requests(self, repository: str, *, state: str = "open", limit: int | None = None) -> list[GitHubPullRequest]:
        self._require_read()
        if state not in {"open", "closed", "all"}:
            raise ValueError("state precisa ser open, closed ou all.")
        return list(self.connector.list_pull_requests(self._repository(repository), state=state, limit=self._limit(limit)))

    def ci_status(self, repository: str, ref: str) -> GitHubCIStatus:
        self._require_read()
        clean_ref = ref.strip()
        if not clean_ref:
            raise ValueError("ref não pode ficar vazio.")
        return self.connector.ci_status(self._repository(repository), clean_ref)

    def create_issue(self, repository: str, title: str, body: str = "", *, confirmed: bool = False) -> GitHubIssue:
        if not self.config.enabled or self.config.access_mode is not GitHubAccessMode.READ_WRITE:
            raise PermissionError("Criação de issue exige modo read_write.")
        if not confirmed:
            raise PermissionError("Criação de issue exige confirmação explícita.")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("title não pode ficar vazio.")
        return self.connector.create_issue(self._repository(repository), clean_title, body.strip())


__all__ = [
    "DisabledGitHubConnector", "GitHubAccessMode", "GitHubCIStatus", "GitHubConfig",
    "GitHubConnector", "GitHubConnectorStatus", "GitHubIssue", "GitHubPullRequest",
    "GitHubRepository", "GitHubService",
]
