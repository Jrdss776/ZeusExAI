# Fase 15.1 — Orquestrador Central

O Orquestrador Central é a camada responsável por classificar comandos de alto nível e encaminhá-los ao módulo correto do ZeusExAI.

## Domínios reconhecidos

- assistente geral;
- análise comercial;
- campanhas;
- Achadinhos do JR;
- agenda;
- dashboard;
- desenvolvimento.

## Segurança

A classificação é local e determinística. O orquestrador não executa operações externas por conta própria. Uma ação somente é executada quando a aplicação registra explicitamente um handler para o domínio correspondente.

Comandos que contêm verbos sensíveis, como publicar, enviar, comprar, excluir, apagar ou executar, são marcados com `requires_confirmation=true`.

## Compatibilidade com OpenJarvis

Comandos não classificados permanecem no domínio `assistant`. Dessa forma, o fluxo original do Jarvis continua disponível como fallback e não é substituído pelas funções comerciais.

## Integração local

A função `build_mobile_orchestrator` conecta os domínios especializados às rotas locais existentes:

| Domínio | Rota local |
| --- | --- |
| Análise comercial | `POST /v1/analysis360` |
| Campanhas | `POST /v1/campaign` |
| Achadinhos | `POST /v1/achadinhos` |
| Agenda | `GET /v1/schedules` |
| Dashboard | `GET /v1/status` |

Os cabeçalhos de autenticação podem ser fornecidos durante a criação do orquestrador. Nenhum token é persistido pelo módulo.

## Exemplo

```python
from openjarvis.zeusex.command_integrations import build_mobile_orchestrator

orchestrator = build_mobile_orchestrator(mobile_api_service, headers=headers)
result = orchestrator.dispatch(
    "Zeus, analise este produto e calcule o ROI",
    {"payload": analysis_payload},
)
```

Quando não existe handler registrado, `handled` permanece falso e nenhuma ação é executada.
