# Fase 15.4 — Sistema de Objetivos

O sistema de objetivos transforma intenções em metas mensuráveis e vinculadas a projetos.

## Estrutura

Cada objetivo registra:

- título e descrição;
- projeto opcional;
- métrica;
- direção (`increase`, `decrease` ou `maintain`);
- valor de referência;
- meta;
- valor atual;
- unidade;
- status;
- prazo opcional;
- histórico de medições.

## Status

- `planned`
- `active`
- `paused`
- `achieved`
- `cancelled`

## Progresso

O progresso é calculado entre o valor de referência e a meta e limitado ao intervalo de 0% a 100%. Metas de redução utilizam o mesmo cálculo com intervalo descendente.

Quando uma medição alcança 100%, o objetivo passa automaticamente para `achieved`. Esse marco é registrado na memória inteligente como uma decisão relevante.

## Integração

- `GoalStore`: persistência SQLite de objetivos e medições;
- `GoalService`: ligação com projetos e memória inteligente;
- `GoalAPIService`: interface JSON local;
- `CommandOrchestrator`: classificação de comandos de metas.

## API local

- `GET /v1/goals`
- `POST /v1/goals`
- `GET /v1/goals/{id}`
- `PATCH /v1/goals/{id}/status`
- `POST /v1/goals/{id}/checkins`

Filtros de listagem:

- `project_id`
- `status`
- `limit`

## Segurança

A implementação não publica dados, não executa ações externas e não oferece exclusão automática pela API. Relações com projetos usam chaves estrangeiras restritivas para evitar perda acidental de contexto.

## Exemplos

Objetivo de crescimento:

```json
{
  "title": "Aumentar vendas",
  "metric": "pedidos mensais",
  "baseline": 100,
  "target": 150,
  "current": 110,
  "unit": "pedidos",
  "direction": "increase",
  "status": "active"
}
```

Medição:

```json
{
  "value": 130,
  "note": "Resultado após nova campanha"
}
```

## Próxima etapa

A Fase 15.5 deve consolidar projetos, objetivos, tarefas, memória, campanhas e análises em um dashboard inteligente único.
