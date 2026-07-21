# Fase 16.6 — Integração operacional opcional com GitHub

A integração GitHub do ZeusExAI é desacoplada de SDKs e tokens. O núcleo fornece contratos, políticas de acesso e uma API local; a aplicação hospedeira é responsável por fornecer um conector autenticado.

## Modos

- `disabled`: padrão seguro;
- `read_only`: consulta repositórios, issues, pull requests e CI;
- `read_write`: mantém as leituras e permite apenas operações explicitamente autorizadas.

## Operações locais

```text
GET  /v1/integrations/github/status
GET  /v1/integrations/github/repositories
GET  /v1/integrations/github/issues
GET  /v1/integrations/github/pull-requests
GET  /v1/integrations/github/ci
POST /v1/integrations/github/issues
```

A criação de issue exige simultaneamente modo `read_write` e confirmação explícita no momento da chamada.

## Validações

- repositórios usam o formato `owner/name`;
- estados aceitos: `open`, `closed` e `all`;
- limites são restringidos pela configuração local;
- referências de CI não podem ficar vazias.

## Segurança

O módulo não persiste tokens, credenciais ou conteúdo remoto. Nesta fase não existem rotas para excluir repositórios, fechar issues, mesclar pull requests, alterar branches, enviar commits ou executar workflows.

## Próxima etapa

A próxima fundação prevista é a integração opcional com canais de comunicação, começando por um contrato genérico de notificações e mensageria com confirmação explícita para envios externos.
