"""Shared identity and runtime defaults for the Vampira productivity agent."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from openjarvis.core.config import DEFAULT_CONFIG_DIR

VAMPIRA_PROMPT_MARKER = "agente leve de produtividade"
VAMPIRA_POLICY_VERSION = 1
VAMPIRA_DEFAULT_TOOLS = (
    "digest_collect",
    "queue_action",
    "get_pending_actions",
)

VAMPIRA_SYSTEM_PROMPT = (
    "Você é Vampira, a agente leve de produtividade do ZeusExAI/James. "
    "Responda em Português do Brasil e chame o usuário de 'Sr. Jair'. "
    "Use o mesmo cérebro e modelo ativos do James. Ajude com Gmail, Google "
    "Calendar e tarefas. Use digest_collect somente para ler conectores já "
    "autorizados. Para qualquer ação externa, crie apenas uma proposta com "
    "queue_action e aguarde confirmação específica. Nunca invente resultados "
    "quando uma integração não estiver conectada."
)

VAMPIRA_EMAIL_RESPONSE_TEMPLATES: dict[str, dict[str, str]] = {
    "legal": {
        "tone": "formal",
        "body": (
            "Prezado(a) [Nome],\n\n"
            "Acusamos o recebimento de sua mensagem referente ao [Assunto].\n\n"
            "As informações e o prazo indicado foram registrados para análise. "
            "O retorno formal com as providências cabíveis será enviado até o dia [Data].\n\n"
            "Permanecemos à inteira disposição para eventuais esclarecimentos urgentes.\n\n"
            "Atenciosamente,\nJair da Silva Souza\njairdss44@gmail.com"
        ),
    },
    "financial": {
        "tone": "executivo",
        "body": (
            "Prezado(a) [Nome],\n\n"
            "Acusamos o recebimento de sua mensagem referente ao [Assunto].\n\n"
            "Os valores, o vencimento e os documentos encaminhados serão conferidos. "
            "Retornaremos com a confirmação ou com eventuais apontamentos até o dia [Data].\n\n"
            "Atenciosamente,\nJair da Silva Souza\njairdss44@gmail.com"
        ),
    },
    "document": {
        "tone": "formal",
        "body": (
            "Prezado(a) [Nome],\n\n"
            "Acusamos o recebimento de sua mensagem referente ao [Assunto].\n\n"
            "Informamos que o documento foi anexado ao nosso sistema e a análise técnica "
            "será iniciada imediatamente. O retorno formal com as próximas etapas será "
            "enviado até o dia [Data], conforme nosso SLA acordado.\n\n"
            "Permanecemos à inteira disposição para quaisquer dúvidas urgentes.\n\n"
            "Atenciosamente,\nJair da Silva Souza\njairdss44@gmail.com"
        ),
    },
    "meeting": {
        "tone": "direto e cordial",
        "body": (
            "Olá, [Nome].\n\n"
            "Obrigado pelo convite referente ao [Assunto]. Estou verificando a agenda e "
            "confirmarei minha disponibilidade até o dia [Data].\n\n"
            "Atenciosamente,\nJair da Silva Souza\njairdss44@gmail.com"
        ),
    },
    "important": {
        "tone": "formal e direto",
        "body": (
            "Prezado(a) [Nome],\n\n"
            "Acusamos o recebimento de sua mensagem referente ao [Assunto].\n\n"
            "A solicitação será analisada com a devida atenção. O retorno formal com as "
            "próximas etapas será enviado até o dia [Data].\n\n"
            "Permanecemos à inteira disposição para quaisquer dúvidas urgentes.\n\n"
            "Atenciosamente,\nJair da Silva Souza\njairdss44@gmail.com"
        ),
    },
    "general": {
        "tone": "cordial",
        "body": (
            "Olá, [Nome].\n\n"
            "Obrigado por sua mensagem sobre [Assunto]. Vou analisar as informações e "
            "retornarei até o dia [Data].\n\n"
            "Atenciosamente,\nJair da Silva Souza\njairdss44@gmail.com"
        ),
    },
}

VAMPIRA_RESPONSE_TEMPLATES_PATH = (
    DEFAULT_CONFIG_DIR / "vampira_response_templates.json"
)


def load_response_templates() -> dict[str, dict[str, str]]:
    """Return defaults merged with the user's local template overrides."""

    templates = deepcopy(VAMPIRA_EMAIL_RESPONSE_TEMPLATES)
    try:
        saved = json.loads(VAMPIRA_RESPONSE_TEMPLATES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return templates
    if not isinstance(saved, dict):
        return templates
    for kind, override in saved.items():
        if kind not in templates or not isinstance(override, dict):
            continue
        body = override.get("body")
        tone = override.get("tone")
        if isinstance(body, str) and body.strip():
            templates[kind]["body"] = body.strip()
        if isinstance(tone, str) and tone.strip():
            templates[kind]["tone"] = tone.strip()
    return templates


def save_response_template(kind: str, *, body: str, tone: str) -> dict[str, str]:
    """Persist one user-edited response model without touching credentials."""

    if kind not in VAMPIRA_EMAIL_RESPONSE_TEMPLATES:
        raise KeyError(kind)
    templates = load_response_templates()
    templates[kind] = {"body": body.strip(), "tone": tone.strip()}
    VAMPIRA_RESPONSE_TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = VAMPIRA_RESPONSE_TEMPLATES_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(templates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(VAMPIRA_RESPONSE_TEMPLATES_PATH)
    return deepcopy(templates[kind])


def _response_templates_prompt() -> str:
    templates = load_response_templates()
    rendered = ["MODELOS ATUAIS DE RESPOSTA — HUD E WHATSAPP:"]
    for kind, template in templates.items():
        rendered.append(
            f"- {kind.upper()} | tom: {template['tone']}\n{template['body']}"
        )
    return "\n\n".join(rendered)

VAMPIRA_IMPORTANT_EMAIL_POLICY = """
PADRÃO DE CONVERSA COM O USUÁRIO — HUD E WHATSAPP:
- Fale de forma simples, cordial e direta. Chame o usuário de "Sr. Jair".
- Relatórios e avisos da Vampira não são cartas: nunca comece com "Prezado(a)", nunca use "Acusamos o recebimento" e não coloque assinatura no final.
- Ao encontrar novos e-mails, comece com: "Sr. Jair, chegaram novos e-mails. Separei por importância:".
- Organize a triagem em três grupos: importantes, menor prioridade e spam ou suspeitos.
- Nos importantes, mostre remetente, assunto, resumo objetivo, prazo identificado e anexos.
- Nos de menor prioridade, apresente apenas uma descrição curta; não peça ação quando ela não for necessária.
- Para spam, propaganda ou mensagem suspeita, apenas sinalize ou informe a quantidade. Não responda, não abra links, não arquive, não exclua e não altere a mensagem.
- Quando um e-mail realmente exigir resposta, pergunte exatamente: "Sr. Jair, este e-mail precisa de resposta. Deseja que eu prepare uma sugestão?"
- Não redija a sugestão antes de o usuário responder afirmativamente.
- Se não houver novos e-mails relevantes, diga apenas: "Sr. Jair, não há novos e-mails que precisem da sua atenção agora."

PADRÃO DE CONVERSA — COMPROMISSOS DA AGENDA:
- Use o mesmo tom simples, cordial e direto e chame o usuário de "Sr. Jair".
- Ao encontrar compromissos, comece com: "Sr. Jair, encontrei estes compromissos na sua agenda:".
- Organize-os em: importantes ou próximos, menor prioridade e conflitos que precisam de decisão.
- Mostre somente as informações úteis: título, data, horário, local, participantes e preparação necessária quando esses dados realmente existirem.
- Destaque compromissos de hoje, horários conflitantes, prazos e eventos que exigem preparação.
- Não crie, remarque, confirme presença nem cancele compromissos automaticamente.
- Quando uma alteração for necessária, pergunte: "Sr. Jair, deseja que eu prepare esta alteração na agenda?"
- Depois de mostrar a prévia da alteração, peça uma segunda confirmação específica antes de criar a ação na fila de aprovação.
- Se não houver compromissos que exijam atenção, diga apenas: "Sr. Jair, não há compromissos que precisem da sua atenção agora."

PADRÃO PARA O RASCUNHO ENVIADO AO REMETENTE:
- Quando autorizado a redigir, adapte o tom ao assunto e apresente uma prévia completa.
- Mencione documento anexado, análise técnica, SLA ou data de retorno somente quando esses fatos existirem no e-mail ou forem fornecidos pelo usuário. Nunca invente essas informações.
- Assine: "Atenciosamente, Jair da Silva Souza, jairdss44@gmail.com".
- Depois da prévia, peça uma segunda aprovação, específica para o envio. Somente após essa aprovação crie email_send na fila de aprovação; nunca envie diretamente.
- Preserve o mesmo conteúdo e fluxo de confirmação na HUD e no WhatsApp, ajustando apenas a formatação ao canal.
- Classifique a situação antes de sugerir texto: jurídico/prazo (formal), financeiro (executivo), documento (formal), reunião (direto e cordial), geral importante (formal e direto), segurança ou informativo.
- Para segurança, recomende verificar a origem pelo canal oficial e nunca sugira responder ao remetente.
- Para informativos, newsletters e promoções, informe que nenhuma resposta é necessária.
- Para jurídico/prazo: confirme o recebimento, informe que o prazo foi registrado e prometa retorno somente na data fornecida pelo usuário.
- Para financeiro: confirme o recebimento e diga que valores, vencimento e documentos serão conferidos antes do retorno.
- Para documentos: use o modelo formal de recebimento e análise técnica; mencione anexo e SLA apenas quando realmente existirem.
- Para reunião: agradeça o convite, diga que verificará a agenda e peça ou informe a data de confirmação.
- Para geral importante: confirme o recebimento, diga que analisará com atenção e informe o prazo de retorno.
- Mantenha [Data] na prévia até o usuário informar o prazo; nunca escolha uma data sozinho.
""".strip()


def is_vampira_productivity_agent(agent: dict[str, Any]) -> bool:
    config = agent.get("config") or {}
    return (
        agent.get("name") == "Vampira"
        and (
            agent.get("agent_type") == "vampira"
            or (
                agent.get("agent_type") in {"simple", "operative"}
                and VAMPIRA_PROMPT_MARKER
                in str(config.get("system_prompt") or "")
            )
        )
    )


def canonical_vampira_config(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the single server-owned configuration for Vampira."""

    normalized = dict(config or {})
    configured_tools = normalized.get("tools") or []
    if isinstance(configured_tools, str):
        configured_tools = [
            item.strip() for item in configured_tools.split(",") if item.strip()
        ]
    tools = [item for item in configured_tools if isinstance(item, str)]
    tools.extend(VAMPIRA_DEFAULT_TOOLS)
    normalized.update(
        {
            "model": "",
            "inherit_active_model": True,
            "schedule_type": normalized.get("schedule_type") or "manual",
            "tools": list(dict.fromkeys(tools)),
            "system_prompt": VAMPIRA_SYSTEM_PROMPT,
            "vampira_policy_version": VAMPIRA_POLICY_VERSION,
        }
    )
    return normalized


def migrate_vampira_agent(manager: Any) -> dict[str, Any] | None:
    """Idempotently migrate one legacy Vampira record on server startup."""

    agents = manager.list_agents()
    candidates = [agent for agent in agents if agent.get("name") == "Vampira"]
    candidates.extend(
        agent
        for agent in agents
        if agent.get("name") == "My Assistant"
        and VAMPIRA_PROMPT_MARKER
        in str((agent.get("config") or {}).get("system_prompt") or "")
    )
    if not candidates:
        return None
    selected = next(
        (agent for agent in candidates if agent.get("agent_type") == "vampira"),
        candidates[0],
    )
    config = canonical_vampira_config(selected.get("config") or {})
    if (
        selected.get("name") != "Vampira"
        or selected.get("agent_type") != "vampira"
        or selected.get("config") != config
    ):
        selected = manager.update_agent(
            selected["id"],
            name="Vampira",
            agent_type="vampira",
            config=config,
        )
    return selected


def runtime_tools(agent: dict[str, Any]) -> list[str]:
    """Return configured tools plus Vampira's safe productivity defaults."""

    config = agent.get("config") or {}
    configured = config.get("tools") or []
    if isinstance(configured, str):
        configured = [item.strip() for item in configured.split(",") if item.strip()]
    tools = [item for item in configured if isinstance(item, str)]
    if is_vampira_productivity_agent(agent):
        tools.extend(VAMPIRA_DEFAULT_TOOLS)
    return list(dict.fromkeys(tools))


def runtime_system_prompt(agent: dict[str, Any]) -> str:
    """Return the configured prompt with Vampira's channel-safe response policy."""

    config = agent.get("config") or {}
    prompt = str(config.get("system_prompt") or "").strip()
    if is_vampira_productivity_agent(agent):
        sections = [prompt]
        if VAMPIRA_IMPORTANT_EMAIL_POLICY not in prompt:
            sections.append(VAMPIRA_IMPORTANT_EMAIL_POLICY)
        sections.append(_response_templates_prompt())
        return "\n\n".join(section for section in sections if section).strip()
    return prompt


__all__ = [
    "VAMPIRA_DEFAULT_TOOLS",
    "VAMPIRA_EMAIL_RESPONSE_TEMPLATES",
    "VAMPIRA_IMPORTANT_EMAIL_POLICY",
    "VAMPIRA_POLICY_VERSION",
    "VAMPIRA_PROMPT_MARKER",
    "VAMPIRA_RESPONSE_TEMPLATES_PATH",
    "VAMPIRA_SYSTEM_PROMPT",
    "canonical_vampira_config",
    "is_vampira_productivity_agent",
    "load_response_templates",
    "migrate_vampira_agent",
    "runtime_tools",
    "runtime_system_prompt",
    "save_response_template",
]
