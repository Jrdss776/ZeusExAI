# Fase 17.5 — Painel de governança do agente

A Fase 17.5 reúne, em uma visão local e somente leitura, os principais dados de governança produzidos pelas Fases 17.1 a 17.4.

## Objetivo

Oferecer uma visão consolidada da fila de planos, aprovações, rejeições, expirações, recibos de execução local, políticas e eventos de auditoria sem adicionar qualquer capacidade de escrita.

## Dados apresentados

- planos visíveis por estado;
- recibos locais recentes;
- políticas registradas por ação;
- eventos recentes de auditoria;
- alertas para revisões pendentes, bloqueios, falhas e timeouts lógicos.

## Contratos locais

- `GET /v1/agent/governance/status`
- `GET /v1/agent/governance/overview`

Essas rotas também são expostas pelo `MobileAPIService` quando o painel é
explicitamente configurado. Elas usam a autenticação local já existente e
retornam `503` quando a dependência não foi habilitada.

Não existem rotas de aprovação, rejeição ou execução nesta camada. Os métodos equivalentes da API retornam `PermissionError`.

## Garantias de segurança

- `read_only=true`;
- `can_approve=false`;
- `can_execute=false`;
- `external_actions_enabled=false`;
- nenhuma credencial é lida ou persistida;
- nenhum plano é alterado;
- nenhuma política é alterada;
- nenhum handler é chamado;
- nenhuma ação externa é habilitada.

## Alertas

O painel sinaliza:

- planos pendentes de revisão;
- execuções bloqueadas;
- falhas recentes;
- timeouts lógicos recentes.

A contagem é calculada apenas sobre a janela visível limitada pelo parâmetro `limit`, cujo máximo é 200.

## Arquivos

- `src/openjarvis/zeusex/agent_governance_dashboard.py`
- `src/openjarvis/zeusex/agent_governance_dashboard_api.py`
- `tests/zeusex/test_agent_governance_dashboard.py`
