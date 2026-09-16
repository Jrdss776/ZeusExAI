"""Vampira — lightweight productivity agent sharing James' active engine."""

from __future__ import annotations

import json
import unicodedata
from typing import Any, Optional

from openjarvis.agents._stubs import AgentContext, AgentResult
from openjarvis.agents.operative import OperativeAgent
from openjarvis.core.registry import AgentRegistry
from openjarvis.core.types import ToolCall


def _plain_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _read_sources(input_text: str) -> list[str]:
    """Select connector reads only when the user is asking to inspect data."""

    text = _plain_text(input_text)
    read_markers = (
        "consulte",
        "consultar",
        "leia",
        "ler ",
        "liste",
        "listar",
        "quantidade",
        "contagem",
        "resumo",
        "recent",
        "pendente",
        "digest_collect",
    )
    if not (_is_count_query(input_text) or any(marker in text for marker in read_markers)):
        return []

    sources: list[str] = []
    if any(marker in text for marker in ("email", "e-mail", "gmail", "caixa de entrada")):
        sources.append("gmail")
    if any(marker in text for marker in ("agenda", "calendario", "compromisso", "reuniao")):
        sources.append("gcalendar")
    if any(marker in text for marker in ("tarefa", "task")):
        sources.append("google_tasks")

    if "digest_collect" in text and not sources:
        sources.extend(("gmail", "gcalendar", "google_tasks"))
    return sources


def _is_count_query(input_text: str) -> bool:
    text = _plain_text(input_text)
    return any(
        marker in text
        for marker in ("quantidade", "contagem", "quantos", "quantas", "numero de")
    )


def _count_response(sources: list[str], metadata: dict[str, Any]) -> str:
    counts = metadata.get("source_counts") or {}
    errors = metadata.get("source_errors") or {}
    labels = {
        "gmail": "E-mails recentes (últimas 24 horas)",
        "gcalendar": "Compromissos de hoje",
        "google_tasks": "Tarefas pendentes",
    }
    lines: list[str] = ["Sr. Jair, verifiquei seus conectores:"]
    for source in sources:
        label = labels.get(source, source)
        if source in errors:
            lines.append(f"{label}: não foi possível consultar o conector.")
        else:
            lines.append(f"{label}: {int(counts.get(source, 0))}.")
    return "\n".join(lines)


@AgentRegistry.register("vampira")
class VampiraAgent(OperativeAgent):
    """Tool-capable Vampira with deterministic, read-only connector preflight.

    Small local models may answer a connector question without emitting a
    function call even when tools are supplied.  Vampira therefore performs
    the authorized read before generation whenever the user's wording clearly
    requests email, calendar, or task data. Aggregate count requests return
    directly from connector metadata; requests requiring interpretation use
    James' active engine/model. No second model or worker is created.
    """

    agent_id = "vampira"

    def run(
        self,
        input: str,
        context: Optional[AgentContext] = None,
        **kwargs: Any,
    ) -> AgentResult:
        sources = _read_sources(input)
        collected = None
        if sources and any(tool.spec.name == "digest_collect" for tool in self._tools):
            plain_input = _plain_text(input)
            count_query = _is_count_query(input)
            if count_query:
                self._emit_turn_start(input)
            collected = self._executor.execute(
                ToolCall(
                    id="vampira-read-1",
                    name="digest_collect",
                    arguments=json.dumps(
                        {
                            "sources": sources,
                            "hours_back": 24,
                            "unacted_only": any(
                                marker in plain_input
                                for marker in ("nao lido", "nao lida", "unread")
                            ),
                            "pending_tasks_only": (
                                "google_tasks" in sources and "pendente" in plain_input
                            ),
                            "today_calendar_only": (
                                "gcalendar" in sources and "hoje" in plain_input
                            ),
                            "count_only": count_query,
                        }
                    ),
                )
            )
            if count_query:
                content = _count_response(sources, collected.metadata)
                self._emit_turn_end(turns=1, content_length=len(content))
                return AgentResult(
                    content=content,
                    tool_results=[collected],
                    turns=1,
                    metadata={"vampira_fast_path": "connector_counts"},
                )
            input = (
                f"{input}\n\n"
                "DADOS REAIS COLETADOS AGORA (fonte exclusiva para a resposta; "
                "não invente nada além deles):\n"
                f"{collected.content or '[nenhum item retornado]'}"
            )

        result = super().run(input, context=context, **kwargs)
        if collected is not None:
            result.tool_results.insert(0, collected)
        return result


__all__ = [
    "VampiraAgent",
    "_count_response",
    "_is_count_query",
    "_read_sources",
]
