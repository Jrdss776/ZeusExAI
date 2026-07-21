# Fase 17.6 — Histórico e relatórios de governança

A Fase 17.6 transforma os registros locais das Fases 17.2 a 17.5 em relatórios históricos somente leitura.

## Objetivo

Permitir acompanhamento temporal da governança sem alterar planos, recibos, políticas ou eventos de auditoria.

## Dados consolidados

- planos por estado;
- execuções por resultado;
- eventos de auditoria por tipo;
- eventos de auditoria por ação;
- totais de bloqueios, falhas e timeouts;
- série diária de planos, execuções e eventos.

## Contratos locais

- `GET /v1/agent/governance/history/status`
- `GET /v1/agent/governance/history?days=30&limit=500`

A classe `AgentGovernanceHistoryAPI` oferece os equivalentes locais `status()` e `report(days, limit)`. A integração HTTP pode delegar essas rotas sem conceder qualquer capacidade de escrita.

## Limites

- período mínimo: 1 dia;
- período máximo: 365 dias;
- janela máxima consultada: 500 itens;
- recibos respeitam o limite de 200 da camada de execução local;
- datas inválidas ou ausentes não entram no relatório.

## Garantias de segurança

- `read_only=true`;
- `can_approve=false`;
- `can_reject=false`;
- `can_execute=false`;
- `external_actions_enabled=false`;
- nenhuma credencial é lida ou persistida;
- nenhum banco recebe escrita durante a geração do relatório;
- nenhum handler de ação é chamado;
- nenhuma integração externa é habilitada.

## Arquivos

- `src/openjarvis/zeusex/agent_governance_history.py`
- `src/openjarvis/zeusex/agent_governance_history_api.py`
- `tests/zeusex/test_agent_governance_history.py`
