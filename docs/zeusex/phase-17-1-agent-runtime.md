# Fase 17.1 — Agent Runtime em modo de planejamento

A Fase 17.1 introduz o runtime do agente ZeusExAI com uma fronteira de
segurança explícita: o runtime pode **planejar**, mas não pode executar ações.

## Objetivo

Conectar os componentes já existentes em um único fluxo de raciocínio
operacional:

- orquestrador de comandos;
- dashboard inteligente;
- memória inteligente;
- projetos e metas representados no dashboard;
- Central Unificada de Integrações.

O resultado é um plano estruturado e explicável para revisão humana.

## Modos

```text
disabled
plan_only
```

Não existe modo de execução na Fase 17.1.

## Fluxo de planejamento

1. validar o comando;
2. classificar localmente o domínio pelo `CommandOrchestrator.route()`;
3. consultar o snapshot do dashboard;
4. consultar o diagnóstico sanitizado das integrações;
5. buscar memórias relacionadas ao comando;
6. preparar etapas específicas para o domínio;
7. destacar ações sensíveis e necessidade de confirmação;
8. devolver o plano sem despachar handlers.

O runtime não chama `CommandOrchestrator.dispatch()`.

## Domínios suportados

- assistant;
- project;
- memory;
- commercial_analysis;
- campaign;
- achadinhos;
- agenda;
- dashboard;
- development.

## Estrutura do plano

Cada plano contém:

```text
id
command
created_at
mode
decision
context
steps
requires_confirmation
executable
execution_blocked_reason
```

Cada etapa informa:

```text
order
kind
title
description
domain
requires_confirmation
executable
blocked_reason
```

Todas as etapas retornam `executable: false` nesta fase.

## Contexto utilizado

O snapshot do plano pode incluir:

- resumo do dashboard;
- alertas do dashboard;
- resumo da Central de Integrações;
- alertas sanitizados de integração;
- memórias relevantes.

O `context` opcional enviado pelo cliente é reservado para a Fase 17.2 e não é
persistido nem utilizado para executar ações nesta fase.

## API local

```text
GET  /v1/agent/status
POST /v1/agent/plans
```

Exemplo de criação:

```json
{
  "command": "mostrar status do projeto"
}
```

Rotas sob `/v1/agent/execute` retornam `405 Method Not Allowed`.

## Segurança

A Fase 17.1 não:

- cria ou modifica projetos;
- grava memórias;
- altera metas;
- cria eventos;
- envia e-mails ou mensagens;
- modifica arquivos no Drive;
- escreve no GitHub;
- executa shell;
- chama handlers do orquestrador;
- persiste planos ou comandos.

Mesmo quando um comando contém termos sensíveis e recebe
`requires_confirmation: true`, o plano continua não executável.

## Testes

A cobertura inclui:

- status `plan_only`;
- composição de contexto;
- classificação por domínio;
- etapa adicional de confirmação;
- bloqueio no modo `disabled`;
- bloqueio de execução mesmo com confirmação;
- validação de comando e contexto;
- API sem rota de execução.

## Próxima fase

A Fase 17.2 poderá introduzir fila local de planos e ciclo de aprovação, ainda
sem execução automática. Qualquer executor futuro deverá possuir política de
permissões por ação, confirmação específica e auditoria local.
