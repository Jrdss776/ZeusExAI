# ZeusExAI 0.9.0-beta.1 — Roteiro de validação

## 1. Instalação

Use Windows 10 ou 11 e Python 3.10–3.13. Crie um ambiente virtual e instale o
repositório conforme `INSTALL_WINDOWS.md`.

## 2. Configuração mínima

Configure `ZEUSEX_DATA_DIR`, um provedor de IA e o modelo. Para OpenAI ou API
compatível, defina a chave somente na sessão atual. Ollama pode ser usado sem
credencial externa.

## 3. Aceitação

```powershell
jarvis zeusex beta-version
jarvis zeusex beta-readiness
jarvis zeusex beta-smoke
jarvis zeusex beta-acceptance
```

A Beta está pronta para uso local quando `beta-acceptance` termina com
`Aceitação Beta: APROVADA`.

## 4. Execução assistida

Comece pelos comandos `status`, `ask` e `chat`. Ative voz, painel móvel e
integrações separadamente. Ações sensíveis devem continuar exigindo confirmação.

## 5. Relatório de problemas

```powershell
jarvis zeusex beta-report --output zeusex-beta-report.json
```

Revise o JSON antes de compartilhar. Descreva também o comando executado, o
resultado esperado e o resultado observado, sem anexar tokens ou chaves.

## 6. Rollback

Encerre processos do ZeusExAI, preserve a pasta definida em `ZEUSEX_DATA_DIR` e
retorne ao código anterior. Não exclua ou substitua bancos sem backup verificado.
No Android/Termux, use o fluxo de backup e restauração documentado antes de cada
atualização.
