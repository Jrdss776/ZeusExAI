# Fase 16.1 — Integração opcional com Google Calendar

## Objetivo

Adicionar uma fundação segura para consultar compromissos e, futuramente, criar eventos no Google Calendar sem tornar a conta Google requisito para o ZeusExAI.

## Princípios

- integração desativada por padrão;
- nenhum token ou segredo é persistido por este módulo;
- SDK Google não é dependência obrigatória do núcleo;
- leitura e escrita usam modos separados;
- criação de eventos exige confirmação explícita;
- nenhuma exclusão ou alteração de evento foi habilitada nesta etapa.

## Modos de acesso

- `disabled`: integração bloqueada;
- `read_only`: permite somente consulta;
- `read_write`: permite consulta e criação confirmada.

## Componentes

### `GoogleCalendarConfig`

Configuração local com modo de acesso, calendário selecionado e limite de resultados.

### `GoogleCalendarConnector`

Contrato que poderá ser implementado por um adaptador Google real. O núcleo não conhece OAuth, SDK ou armazenamento de credenciais.

### `DisabledGoogleCalendarConnector`

Implementação padrão segura. Retorna estado desativado e bloqueia operações externas.

### `GoogleCalendarService`

Aplica validação de intervalo, limites, permissões e confirmação antes de chamar o conector.

### `GoogleCalendarAPI`

Camada JSON local com as rotas:

```text
GET  /v1/integrations/google-calendar/status
GET  /v1/integrations/google-calendar/events
POST /v1/integrations/google-calendar/events
POST /v1/integrations/google-calendar/events/preview
```

A criação via `POST` só funciona em modo `read_write` e com confirmação explícita fornecida pela aplicação hospedeira.

A rota `/preview` valida título, intervalo, localização e calendário inteiramente
no processo local. Ela não exige autenticação, não chama o conector e informa
explicitamente que nenhuma ação externa foi executada.

## Dashboard

O dashboard inteligente agora inclui:

- estado sanitizado da integração;
- próximos eventos dos sete dias seguintes quando a leitura está habilitada;
- quantidade de compromissos futuros no resumo;
- alerta controlado quando o conector configurado está indisponível.

Com a integração desativada, nenhuma consulta externa é iniciada.

## Segurança

O módulo nunca:

- lê credenciais de arquivos sem solicitação;
- salva refresh tokens;
- envia eventos automaticamente;
- altera ou exclui compromissos existentes;
- habilita rede por padrão.

## Próximos passos

1. implementar adaptador OAuth opcional em pacote separado;
2. adicionar armazenamento seguro de credenciais fornecido pelo sistema operacional;
3. implementar uma interface visual para revisar a pré-visualização;
4. avançar para Gmail e Google Drive mantendo o mesmo contrato de permissão.
