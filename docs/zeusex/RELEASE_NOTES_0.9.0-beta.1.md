# ZeusExAI 0.9.0-beta.1

Primeira versão Beta pública do ZeusExAI, uma distribuição personalizada e local-first baseada no OpenJarvis, com interface e documentação prioritariamente em português do Brasil.

## Principais recursos

- assistente modular com memória SQLite e runtime persistente;
- CLI, provedores de IA, Skills, voz opcional e automação local segura;
- análise comercial para Shopee e Mercado Livre;
- cálculos de lucro, margem, ROI, equilíbrio e Análise 360;
- projetos, metas, agendamento e dashboard;
- integrações opcionais e desacopladas com Google, GitHub e canais de comunicação;
- planejamento, aprovação e execução governada de ações locais registradas;
- painel e histórico de governança somente-leitura;
- suporte a Windows 10/11 e núcleo utilizável no Android por Termux;
- diagnóstico, relatório sanitizado, smoke test e aceitação da Beta.

## Segurança

- ações externas permanecem desativadas por padrão;
- não há shell arbitrário no executor governado;
- operações sensíveis exigem confirmação;
- credenciais não são persistidas pelo núcleo;
- painel móvel restrito ao loopback local e protegido por token em memória;
- decisões operacionais ficam registradas para auditoria.

## Compatibilidade

- Python 3.10, 3.11, 3.12 e 3.13;
- Windows 10 ou 11;
- Android com Termux para os recursos compatíveis;
- voz, painel móvel e integrações são opcionais.

## Instalação

Consulte:

- `docs/zeusex/INSTALL_WINDOWS.md`;
- `docs/zeusex/INSTALL_TERMUX.md`;
- `docs/zeusex/ANDROID_LOCAL_SERVER.md`;
- `docs/zeusex/BETA_RUNBOOK.md`.

## Validação

Após instalar e configurar um provedor de IA, execute:

```
jarvis zeusex beta-version
jarvis zeusex beta-readiness
jarvis zeusex beta-smoke
jarvis zeusex beta-acceptance
```

A instalação está pronta quando o último comando informa `Aceitação Beta: APROVADA`.

## Limitações conhecidas

- esta é uma versão Beta e deve ser publicada como pré-lançamento;
- o painel Android ainda depende do Termux e do servidor local;
- integrações externas precisam ser ativadas e configuradas separadamente;
- ações externas reais continuam indisponíveis ou desativadas por padrão;
- backends de voz podem exigir dependências e configuração específicas do sistema.

## Suporte e diagnóstico

Para gerar um relatório sanitizado:

```
jarvis zeusex beta-report --output zeusex-beta-report.json
```

Revise o arquivo antes de compartilhá-lo. Não envie chaves, tokens ou credenciais.

## Rollback

Encerre os processos do ZeusExAI, preserve `ZEUSEX_DATA_DIR` e retorne ao commit ou à versão anterior. No Android, faça backup verificado antes de atualizar ou restaurar bancos.
