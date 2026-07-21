# Fase 16.2 — Integração opcional com Gmail

O ZeusExAI possui contratos locais para integração com Gmail sem tornar OAuth,
SDKs Google ou uma conta conectada requisitos obrigatórios do núcleo.

## Modos

- `disabled`: padrão seguro;
- `read_only`: consulta mensagens sem alterar a caixa postal;
- `draft_and_send`: permite envio somente após confirmação explícita.

A primeira entrega operacional da fase prioriza leitura, resumo e triagem. O
módulo não marca mensagens como lidas, não arquiva e não exclui conteúdo.

## Operações

```text
GET  /v1/integrations/gmail/status
GET  /v1/integrations/gmail/messages
GET  /v1/integrations/gmail/triage
POST /v1/integrations/gmail/drafts/preview
POST /v1/integrations/gmail/messages/send
```

`GET /messages` aceita `q` e `limit`, devolvendo mensagens e resumos locais.
`GET /triage` usa `in:inbox` por padrão e classifica cada mensagem como:

- `urgent`;
- `needs_reply`;
- `unread`;
- `fyi`.

A classificação é determinística, baseada em sinais explícitos no assunto e na
prévia, como prazo, urgência, pedido de retorno ou confirmação. Ela não executa
ações na caixa postal.

## Resumo local

O resumo utiliza apenas assunto e `snippet` fornecidos pelo conector. O texto é
limitado e não depende de IA externa. Mensagens sem prévia recebem uma indicação
explícita de conteúdo indisponível.

## Escrita protegida

A prévia valida destinatários, assunto e corpo localmente e informa
`external_action_performed: false`. O envio exige simultaneamente:

1. integração habilitada;
2. modo `draft_and_send`;
3. conector autenticado fornecido pela aplicação hospedeira;
4. confirmação explícita no momento da ação.

Nenhuma credencial, token, mensagem ou rascunho é persistido por este módulo.
Exclusão, arquivamento, marcação e alteração de mensagens não estão disponíveis.

## Painel móvel local

A PWA pode consultar o estado da integração, listar mensagens e exibir a triagem.
O servidor móvel não precisa expor envio real. A confirmação permanece restrita
à aplicação hospedeira.

## Próximos passos

1. adaptador OAuth opcional em pacote separado;
2. armazenamento de credenciais pelo sistema operacional;
3. sincronização seletiva de metadados, sem conteúdo integral;
4. Fase 16.3 — fundação equivalente para Google Drive.
