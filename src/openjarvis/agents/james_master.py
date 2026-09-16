"""James master agent: lightweight routing across specialist roles.

The specialists are prompt profiles sharing the same inference engine.  This
keeps memory use close to a single-agent chat while still giving James an
explicit orchestration step for each request.
"""

from __future__ import annotations

import re
from typing import Optional

from openjarvis.agents._stubs import AgentContext, AgentResult
from openjarvis.agents.orchestrator import OrchestratorAgent
from openjarvis.core.registry import AgentRegistry
from openjarvis.core.types import Message, Role


_SPECIALISTS = (
    (
        "sistema_windows",
        re.compile(
            r"\b(organizar|mover|renomear|pasta|arquivo|fechar|encerrar|desligar|"
            r"programa|aplicativo|processo|manuten(?:ç|c)[aã]o|diagn[oó]stico|"
            r"otimizar|limpeza|computador|windows|disco)\b",
            re.IGNORECASE,
        ),
        "Especialista em Windows e organizacao local: use pc_status, process_list "
        "e folder_organizer_preview para inspecoes somente leitura. Para encerrar "
        "um programa, primeiro obtenha PID e nome e depois use queue_action com "
        "action_type local_process_close, payload {pid, expected_name} e tier high. "
        "Para organizar uma pasta, primeiro gere a previa e depois use queue_action "
        "com action_type local_organize_folder, payload {path, snapshot_hash} e tier "
        "high. Informe que a acao aguarda aprovacao no sino; nunca diga que executou "
        "antes de receber o resultado da fila.",
    ),
    (
        "design_grafico",
        re.compile(
            r"\b(design(?:er)?|design gr[aá]fico|arte|logo|logotipo|banner|flyer|"
            r"cartaz|panfleto|folder|carrossel|thumbnail|mockup|embalagem|r[oó]tulo|"
            r"identidade visual|paleta|tipografia|layout|composi(?:ção|cao)|"
            r"social media|post(?:agem)?|imagem promocional|material gr[aá]fico)\b",
            re.IGNORECASE,
        ),
        "Especialista em design grafico e direcao de arte: transforme o pedido em "
        "um briefing objetivo; defina formato, hierarquia visual, composicao, "
        "paleta, tipografia e chamada principal de acordo com o publico e o canal. "
        "Quando a ferramenta permitir criar ou editar imagens, produza a peca e "
        "revise legibilidade, contraste, alinhamento, margens e consistencia visual. "
        "Quando nao permitir, entregue especificacoes e um prompt de producao "
        "prontos para uso. Preserve a identidade da marca fornecida, nao invente "
        "logotipos, fontes licenciadas ou ativos ausentes e solicite somente as "
        "informacoes essenciais que realmente impedirem o trabalho.",
    ),
    (
        "codigo",
        re.compile(
            r"\b(c[oó]digo|programa(?:r|ção)?|python|javascript|typescript|"
            r"html|css|api|bug|erro de compila|script|banco de dados)\b",
            re.IGNORECASE,
        ),
        "Especialista em codigo: analise tecnicamente, proponha mudancas pequenas, "
        "preserve o projeto existente, use file_read/git_status/git_diff para obter "
        "evidencias e code_interpreter para validar trechos seguros. Verifique riscos "
        "antes de executar algo e nunca invente resultados de testes.",
    ),
    (
        "comunicacao",
        re.compile(
            r"\b(e-?mail|mensagem|responder|resposta|an[uú]ncio|texto|roteiro|"
            r"publica(?:r|ção)|cliente|whatsapp)\b",
            re.IGNORECASE,
        ),
        "Especialista em comunicacao: produza textos claros no tom pedido. "
        "Nunca envie ou publique nada sem autorizacao explicita do usuario.",
    ),
    (
        "pesquisa",
        re.compile(
            r"\b(pesquis|busc|procure|compare|fonte|documento|dados|not[ií]cia|"
            r"informa(?:ção|ções)|descubra)\b",
            re.IGNORECASE,
        ),
        "Especialista em pesquisa: consulte primeiro o contexto e as fontes "
        "disponiveis, diferencie fatos de inferencias e nao invente referencias.",
    ),
    (
        "memoria_analise",
        re.compile(
            r"\b(lembre|mem[oó]ria|second brain|hist[oó]rico|resum|analis|"
            r"planej|estrat[eé]gia|contexto)\b",
            re.IGNORECASE,
        ),
        "Especialista em memoria e analise: use o contexto global fornecido, "
        "organize evidencias e explicite lacunas antes de concluir.",
    ),
)

_MASTER_PROMPT = """Seu nome e James. Voce e o Agente Mestre do ZeusExAI e o
usuario nunca deve ser chamado de James sem informar esse nome. Entenda o pedido,
use o contexto global e coordene o perfil especialista indicado abaixo. Responda
em portugues do Brasil. Use ferramentas somente quando forem realmente uteis.
Antes de qualquer acao externa, destrutiva, envio, publicacao ou alteracao de
arquivos, solicite autorizacao. Entregue ao usuario uma resposta unica e clara;
nao exponha raciocinio interno nem simule resultados de ferramentas.

Especialista selecionado: {specialist}
Instrucao do especialista: {instruction}
"""


@AgentRegistry.register("james_master")
class JamesMasterAgent(OrchestratorAgent):
    """Route requests to a specialist profile without loading another model."""

    agent_id = "james_master"
    _default_max_turns = 2
    _default_temperature = 0.3
    _default_max_tokens = 512

    @staticmethod
    def select_specialist(text: str) -> tuple[str, str]:
        for name, pattern, instruction in _SPECIALISTS:
            if pattern.search(text):
                return name, instruction
        return (
            "geral",
            "Especialista geral: responda diretamente, com objetividade, e "
            "encaminhe para uma ferramenta apenas se houver necessidade concreta.",
        )

    def run(
        self,
        input: str,
        context: Optional[AgentContext] = None,
        **kwargs,
    ) -> AgentResult:
        specialist, instruction = self.select_specialist(input)
        ctx = context or AgentContext()
        prompt = _MASTER_PROMPT.format(
            specialist=specialist,
            instruction=instruction,
        )
        # Keep memory-injected system context and add the master identity first.
        ctx.conversation.messages.insert(
            0,
            Message(role=Role.SYSTEM, content=prompt),
        )
        result = super().run(input, context=ctx, **kwargs)
        result.metadata["specialist"] = specialist
        result.metadata["orchestrated_by"] = "james_master"
        return result


__all__ = ["JamesMasterAgent"]
