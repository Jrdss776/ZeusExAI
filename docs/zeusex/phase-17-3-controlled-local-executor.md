# Fase 17.3 — Executor local controlado

A Fase 17.3 introduz execução restrita para planos aprovados. O executor não recebe
comandos livres e não acessa integrações externas. Ele opera somente sobre um catálogo
explícito de ações locais, idempotentes e previamente registradas.

## Condições obrigatórias

Uma execução só pode ocorrer quando todas as condições abaixo forem atendidas:

1. o plano existe na fila local;
2. o estado atual do plano é `approved`;
3. a solicitação contém confirmação explícita;
4. a ação está registrada no catálogo local;
5. a ação declara `local_only=true`;
6. a ação declara `idempotent=true`;
7. o nome da ação não pertence a uma integração externa bloqueada.

Planos `pending`, `rejected` ou `expired` não podem ser executados.

## Ações iniciais

```text
system.information
filesystem.list_directory
```

`system.information` retorna informações básicas do sistema e da versão do Python.

`filesystem.list_directory` lista no máximo 50 entradas de um único diretório, sem
recursão e sem executar comandos de shell.

## Bloqueios externos

Os seguintes prefixos são rejeitados pelo registro e pela execução:

```text
calendar.
gmail.
drive.
github.
whatsapp.
telegram.
slack.
http.
shell.
subprocess.
```

A Fase 17.3 não envia mensagens, não altera agenda, não manipula e-mails, não acessa
Google Drive, não escreve no GitHub e não executa shell arbitrário.

## Idempotência

O executor calcula uma chave SHA-256 usando:

- identificador da fila;
- identificador do plano;
- nome da ação;
- argumento normalizado.

Uma repetição com a mesma combinação retorna o recibo existente e não chama novamente
o handler. Argumentos diferentes geram chaves e recibos diferentes.

## Recibos locais

Cada execução bem-sucedida registra em SQLite:

- `queue_id`;
- `plan_id`;
- ação;
- chave de idempotência;
- estado;
- saída textual;
- data e hora UTC.

Nenhuma credencial ou token é armazenado.

## API local

Contratos previstos:

```text
GET  /v1/agent/executor/status
GET  /v1/agent/executor/actions
POST /v1/agent/queue/{id}/execute-local
GET  /v1/agent/executor/receipts
```

A execução recebe:

```json
{
  "action": "system.information",
  "argument": "",
  "confirmed": true
}
```

## Limites desta fase

- não há execução automática;
- não há interpretação de comandos livres pelo executor;
- não há encadeamento de múltiplas ações;
- não há conectores externos;
- não há subprocessos ou shell;
- aprovação e confirmação continuam sendo eventos separados.

A próxima etapa prevista é a Fase 17.4, dedicada a políticas de execução, auditoria
detalhada e limites operacionais por ação.
