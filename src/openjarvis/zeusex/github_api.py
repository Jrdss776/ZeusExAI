"""API local para a integração opcional com GitHub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from openjarvis.zeusex.github_integration import GitHubService


@dataclass(frozen=True, slots=True)
class GitHubAPIResponse:
    status: int
    body: dict[str, Any]


class GitHubAPI:
    def __init__(self, service: GitHubService) -> None:
        self.service = service

    @staticmethod
    def _error(status: int, message: str) -> GitHubAPIResponse:
        return GitHubAPIResponse(status, {"ok": False, "error": message})

    def dispatch(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        query: Mapping[str, str] | None = None,
        confirmed: bool = False,
    ) -> GitHubAPIResponse:
        verb = method.strip().upper()
        route = "/" + path.strip("/")
        payload = dict(body or {})
        params = dict(query or {})
        try:
            if verb == "GET" and route == "/v1/integrations/github/status":
                return GitHubAPIResponse(200, {"ok": True, "status": self.service.status().to_dict()})
            if verb == "GET" and route == "/v1/integrations/github/repositories":
                items = self.service.list_repositories(limit=int(params["limit"]) if params.get("limit") else None)
                return GitHubAPIResponse(200, {"ok": True, "items": [item.to_dict() for item in items]})
            if verb == "GET" and route == "/v1/integrations/github/issues":
                items = self.service.list_issues(
                    params.get("repository", ""),
                    state=params.get("state", "open"),
                    limit=int(params["limit"]) if params.get("limit") else None,
                )
                return GitHubAPIResponse(200, {"ok": True, "items": [item.to_dict() for item in items]})
            if verb == "GET" and route == "/v1/integrations/github/pull-requests":
                items = self.service.list_pull_requests(
                    params.get("repository", ""),
                    state=params.get("state", "open"),
                    limit=int(params["limit"]) if params.get("limit") else None,
                )
                return GitHubAPIResponse(200, {"ok": True, "items": [item.to_dict() for item in items]})
            if verb == "GET" and route == "/v1/integrations/github/ci":
                status = self.service.ci_status(params.get("repository", ""), params.get("ref", ""))
                return GitHubAPIResponse(200, {"ok": True, "ci": status.to_dict()})
            if verb == "POST" and route == "/v1/integrations/github/issues":
                issue = self.service.create_issue(
                    str(payload.get("repository") or ""),
                    str(payload.get("title") or ""),
                    str(payload.get("body") or ""),
                    confirmed=confirmed,
                )
                return GitHubAPIResponse(201, {"ok": True, "issue": issue.to_dict()})
        except PermissionError as exc:
            return self._error(403, str(exc))
        except (TypeError, ValueError) as exc:
            return self._error(400, str(exc))
        except RuntimeError as exc:
            return self._error(503, str(exc))
        return self._error(404, "Rota não encontrada.")


__all__ = ["GitHubAPI", "GitHubAPIResponse"]
