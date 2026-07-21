# Fase 16.5 — Prévia segura de configuração OAuth Google

Esta fase adiciona um plano auditável de permissões para Calendar, Gmail e Drive.
A prévia usa apenas escopos de leitura e metadados e não inicia OAuth, não recebe
segredos e não persiste tokens.

```text
POST /v1/integrations/google/setup/preview
```

O callback permitido precisa usar HTTP no loopback local. A resposta informa as
integrações escolhidas, os escopos mínimos e que uma autorização futura do usuário
será obrigatória. Não existe rota `connect` nesta fase.
