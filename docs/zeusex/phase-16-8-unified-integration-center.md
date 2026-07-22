# Fase 16.8 — Central Unificada de Integrações

A Central Unificada reúne o diagnóstico sanitizado das integrações opcionais do
ZeusExAI sem executar ações externas e sem expor credenciais, tokens, mensagens
ou dados privados dos provedores.

## Integrações observadas

- Google Calendar;
- Gmail;
- Google Drive;
- GitHub;
- notificações locais;
- WhatsApp;
- Telegram;
- Slack.

## Endpoint local

```text
GET /v1/integrations/overview
```

O endpoint é exclusivamente de leitura. Métodos de escrita não são aceitos.

## Estados normalizados

```text
disabled
authentication_required
ready
error
```

O resumo geral pode retornar:

```text
disabled
ready
attention_required
degraded
```

- `disabled`: nenhuma integração está habilitada;
- `ready`: integrações habilitadas e autenticadas, sem alertas;
- `attention_required`: existe integração habilitada aguardando autenticação;
- `degraded`: pelo menos um componente falhou durante o diagnóstico.

## Alertas

A central gera alertas sanitizados para:

- autenticação necessária;
- falha ao consultar o estado de um componente.

Integrações desativadas intencionalmente não geram alertas.

Cada alerta contém somente:

```text
integration
severity
code
message
```

Exceções internas, tokens, motivos fornecidos por provedores e conteúdo das
contas não são retornados pela central.

## Segurança

A Central Unificada:

- não envia mensagens;
- não cria eventos;
- não modifica e-mails;
- não altera arquivos;
- não cria issues;
- não inicia OAuth;
- não renova credenciais;
- não persiste histórico de sincronização;
- não armazena tokens ou segredos.

As operações continuam restritas aos serviços específicos, respeitando os
modos de acesso e as confirmações explícitas definidos em cada integração.

## Arquivos

```text
src/openjarvis/zeusex/integration_center.py
src/openjarvis/zeusex/integration_center_api.py
tests/zeusex/test_integration_center.py
```

## Próxima etapa

A Fase 17 introduzirá o Agent Runtime do ZeusExAI. Ele poderá consultar esta
central antes de planejar uma ação, evitando fluxos que dependam de conectores
desativados, não autenticados ou degradados.
