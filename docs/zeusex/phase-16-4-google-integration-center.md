# Fase 16.4 — Central de Integrações Google

A Central Google reúne o estado de Calendar, Gmail e Drive sem consultar ou
exibir tokens, identificadores de conta ou mensagens internas dos conectores.

```text
GET /v1/integrations/google/status
```

O diagnóstico informa apenas se cada integração está habilitada, autenticada e
qual modo de acesso foi autorizado. Falhas são convertidas para o estado genérico
`error`, evitando que detalhes potencialmente confidenciais cheguem ao painel.

A rota é somente leitura, protegida pela autenticação local já existente e fica
disponível no painel móvel pelo botão **Verificar integrações**.
