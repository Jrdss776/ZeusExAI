# Fase 17.2 — Fila local de planos e ciclo de aprovação

## Objetivo

Adicionar persistência local e revisão humana aos planos produzidos pelo Agent Runtime, sem habilitar execução automática.

## Estados

- `pending`: aguardando revisão;
- `approved`: aprovado para referência futura;
- `rejected`: rejeitado pelo revisor;
- `expired`: expirado antes da revisão.

Somente planos `pending` podem ser aprovados ou rejeitados.

## Persistência

A fila usa SQLite local. Cada registro armazena:

- identificador interno;
- `plan_id` original;
- comando;
- domínio;
- estado;
- necessidade de confirmação;
- payload sanitizado do plano;
- criação e expiração;
- data e nota de revisão.

## Expiração

O TTL padrão é 60 minutos e pode ser configurado entre 1 e 43.200 minutos. Planos vencidos são marcados como `expired` quando a fila é consultada ou quando `expire_due()` é chamado.

## API local

Contrato previsto:

```text
GET  /v1/agent/queue/status
POST /v1/agent/queue
GET  /v1/agent/queue
GET  /v1/agent/queue/{id}
POST /v1/agent/queue/{id}/approve
POST /v1/agent/queue/{id}/reject
```

Uma tentativa de execução permanece bloqueada:

```text
POST /v1/agent/queue/{id}/execute
```

O serviço responde com erro de permissão mesmo para planos aprovados e mesmo quando `confirmed=true`.

## Segurança

A aprovação não é autorização de execução. Ela apenas registra a decisão humana e prepara a separação entre planejamento, governança e uma futura camada executora.

A Fase 17.2 não:

- chama `AgentRuntime.execute()`;
- chama conectores externos;
- envia mensagens;
- cria eventos;
- escreve no GitHub;
- modifica Gmail ou Drive;
- persiste tokens.

## Testes

A cobertura inclui:

- inclusão e leitura de planos;
- aprovação e rejeição;
- transição única de revisão;
- filtro por estado;
- expiração automática;
- TTL inválido;
- bloqueio absoluto da execução.
