# ZeusExAI 0.9.0-beta.2

Segunda versão Beta pública do ZeusExAI. Esta atualização conclui a integração
do painel visual de Governança com o runtime móvel usado em instalações normais.

## Destaques

- nova página visual de Governança com status, alertas, métricas e histórico;
- composição automática das APIs de Governança no `mobile-api` e `mobile-serve`;
- bancos SQLite persistentes e compartilhados para fila, recibos e auditoria;
- eliminação do erro 503 causado pela ausência de injeção dos serviços;
- autenticação local e restrição do servidor ao loopback preservadas.

## Fronteira de segurança

- o painel permanece estritamente somente leitura;
- aprovação, rejeição, execução e ações externas continuam desativadas;
- não foram adicionadas rotas de escrita ao painel;
- o executor governado continua limitado às ações locais registradas;
- tokens e credenciais não são incluídos em relatórios de suporte.

## Validação

- testes da API garantem uso exclusivo dos quatro endpoints `GET` de Governança;
- testes do runtime confirmam persistência e compartilhamento dos bancos locais;
- testes da CLI confirmam status 200 e modo `read_only` no fluxo real;
- CI, integração do instalador e documentação aprovados antes da promoção.

Para a aceitação final, execute:

```text
jarvis zeusex beta-version
jarvis zeusex beta-readiness
jarvis zeusex beta-smoke
jarvis zeusex beta-acceptance
```

O último comando deve informar `Aceitação Beta: APROVADA`.

## Atualização e rollback

Faça backup verificado de `ZEUSEX_DATA_DIR` antes de atualizar, especialmente no
Android/Termux. Para voltar à beta.1, encerre o servidor, preserve a pasta de
dados e reinstale a tag `v0.9.0-beta.1`. Os bancos locais não devem ser apagados.

## Limitações conhecidas

- esta versão deve ser publicada como pré-lançamento;
- o painel Android ainda depende do Termux e do servidor local;
- integrações externas exigem configuração separada;
- distribuição PyPI e instaladores assinados dependem das credenciais do projeto.
