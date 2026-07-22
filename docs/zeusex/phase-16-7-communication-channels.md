# Fase 16.7 — Canais de comunicação e notificações

O ZeusExAI possui uma camada opcional e desacoplada para notificações locais e
canais externos. Nenhum SDK, token ou conta é requisito do núcleo.

## Canais

- `local`;
- `whatsapp`;
- `telegram`;
- `slack`.

## Modos

- `disabled`: padrão seguro;
- `preview_only`: permite gerar prévias e notificações locais;
- `send_confirmed`: permite envio externo somente após confirmação explícita.

## Operações locais

```text
GET  /v1/integrations/communications/status
POST /v1/integrations/communications/preview
POST /v1/integrations/communications/send
POST /v1/integrations/communications/broadcast
```

A prévia nunca executa ação externa e retorna
`external_action_performed: false`. O envio para WhatsApp, Telegram ou Slack
exige, simultaneamente:

1. modo `send_confirmed`;
2. conector do canal fornecido pela aplicação hospedeira;
3. conector habilitado e autenticado;
4. confirmação explícita no momento da chamada.

Notificações `local` não usam rede e podem ser entregues em `preview_only`.

## Segurança

O módulo não persiste tokens, mensagens, destinatários ou recibos. Também não
implementa leitura de conversas, automação de respostas, importação de contatos,
webhooks públicos ou disparos silenciosos.

O envio em lote reutiliza a mesma política de confirmação de cada mensagem. Se
um canal externo estiver indisponível, o envio falha de forma explícita em vez
de trocar de canal automaticamente.

## Próximos passos

1. adaptadores opcionais separados para cada provedor;
2. armazenamento de segredos pelo sistema operacional;
3. filas locais auditáveis e limites de frequência;
4. preferências de canal por tipo de alerta;
5. integração com o dashboard inteligente.
