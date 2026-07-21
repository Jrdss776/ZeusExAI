# Fase 16.2 — Fundação opcional do Gmail

O ZeusExAI possui contratos locais para futura integração com Gmail sem tornar
OAuth, SDKs Google ou uma conta conectada requisitos do núcleo.

## Modos

- `disabled`: padrão seguro;
- `read_only`: consulta mensagens sem alterar a caixa postal;
- `draft_and_send`: permite envio somente após confirmação explícita.

## Operações

```text
GET  /v1/integrations/gmail/status
GET  /v1/integrations/gmail/messages
POST /v1/integrations/gmail/drafts/preview
POST /v1/integrations/gmail/messages/send
```

A prévia valida destinatários, assunto e corpo localmente. Ela não exige rede e
informa `external_action_performed: false`. O envio exige simultaneamente:

1. integração habilitada;
2. modo `draft_and_send`;
3. conector autenticado fornecido pela aplicação hospedeira;
4. confirmação explícita no momento da ação.

Nenhuma credencial, token, mensagem ou rascunho é persistido por este módulo.
Exclusão, arquivamento, marcação e alteração de mensagens não estão disponíveis.

## Próximos passos

1. adaptador OAuth opcional em pacote separado;
2. armazenamento de credenciais pelo sistema operacional;
3. triagem visual somente-leitura;
4. pré-visualização de respostas no painel móvel;
5. fundação equivalente para Google Drive.
