import pytest

from openjarvis.zeusex.github_api import GitHubAPI
from openjarvis.zeusex.github_integration import (
    GitHubAccessMode,
    GitHubCIStatus,
    GitHubConfig,
    GitHubConnectorStatus,
    GitHubIssue,
    GitHubPullRequest,
    GitHubRepository,
    GitHubService,
)


class FakeGitHubConnector:
    def __init__(self) -> None:
        self.created = []

    def status(self):
        return GitHubConnectorStatus(True, "read_write", True)

    def list_repositories(self, *, limit):
        return [GitHubRepository("Jrdss776/ZeusExAI", False, "main", 2)] * min(limit, 1)

    def list_issues(self, repository, *, state, limit):
        return [GitHubIssue(1, f"Issue em {repository}", state)] * min(limit, 1)

    def list_pull_requests(self, repository, *, state, limit):
        return [GitHubPullRequest(1, f"PR em {repository}", state, "develop", "main", True)] * min(limit, 1)

    def ci_status(self, repository, ref):
        return GitHubCIStatus(ref, "success", 4, 0)

    def create_issue(self, repository, title, body):
        issue = GitHubIssue(2, title, "open")
        self.created.append((repository, title, body))
        return issue


def test_github_is_disabled_by_default() -> None:
    service = GitHubService()
    assert service.status().enabled is False
    with pytest.raises(PermissionError):
        service.list_repositories()


def test_read_only_allows_reads_and_blocks_issue_creation() -> None:
    service = GitHubService(FakeGitHubConnector(), GitHubConfig(True, GitHubAccessMode.READ_ONLY))
    assert service.list_repositories()[0].full_name == "Jrdss776/ZeusExAI"
    assert service.list_issues("Jrdss776/ZeusExAI")[0].number == 1
    assert service.list_pull_requests("Jrdss776/ZeusExAI")[0].mergeable is True
    assert service.ci_status("Jrdss776/ZeusExAI", "develop").state == "success"
    with pytest.raises(PermissionError):
        service.create_issue("Jrdss776/ZeusExAI", "Teste", confirmed=True)


def test_write_requires_explicit_confirmation() -> None:
    connector = FakeGitHubConnector()
    service = GitHubService(connector, GitHubConfig(True, GitHubAccessMode.READ_WRITE))
    with pytest.raises(PermissionError):
        service.create_issue("Jrdss776/ZeusExAI", "Teste")
    issue = service.create_issue("Jrdss776/ZeusExAI", "Teste", "Corpo", confirmed=True)
    assert issue.number == 2
    assert connector.created == [("Jrdss776/ZeusExAI", "Teste", "Corpo")]


def test_repository_and_state_validation() -> None:
    service = GitHubService(FakeGitHubConnector(), GitHubConfig(True, GitHubAccessMode.READ_ONLY))
    with pytest.raises(ValueError, match="owner/name"):
        service.list_issues("invalido")
    with pytest.raises(ValueError, match="state"):
        service.list_pull_requests("Jrdss776/ZeusExAI", state="draft")


def test_api_exposes_reads_and_protects_writes() -> None:
    connector = FakeGitHubConnector()
    api = GitHubAPI(GitHubService(connector, GitHubConfig(True, GitHubAccessMode.READ_WRITE)))

    repos = api.dispatch("GET", "/v1/integrations/github/repositories")
    ci = api.dispatch(
        "GET",
        "/v1/integrations/github/ci",
        query={"repository": "Jrdss776/ZeusExAI", "ref": "develop"},
    )
    blocked = api.dispatch(
        "POST",
        "/v1/integrations/github/issues",
        {"repository": "Jrdss776/ZeusExAI", "title": "Nova issue"},
    )
    created = api.dispatch(
        "POST",
        "/v1/integrations/github/issues",
        {"repository": "Jrdss776/ZeusExAI", "title": "Nova issue"},
        confirmed=True,
    )

    assert repos.status == 200
    assert ci.body["ci"]["state"] == "success"
    assert blocked.status == 403
    assert created.status == 201
