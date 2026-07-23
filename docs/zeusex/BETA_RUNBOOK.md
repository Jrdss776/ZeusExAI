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

## 7. Publicação

A publicação deve usar a tag `v0.9.0-beta.1` apontando para o commit validado da
branch `main`. Antes de criar a release, confirme:

- todos os checks remotos aprovados;
- `beta-acceptance` com resultado `Aceitação Beta: APROVADA`;
- notas da release revisadas;
- ações externas desativadas por padrão;
- instruções de instalação e rollback disponíveis.

Publique como **pré-lançamento**. Não marque esta versão como `latest` estável.

### Distribuição opcional

A release fonte no GitHub não depende da publicação no PyPI nem de instaladores
Desktop. Esses canais permanecem desativados até que suas credenciais externas
estejam configuradas:

- cadastre o Trusted Publisher no PyPI para este repositório, workflow e ambiente;
- defina `PYPI_PUBLISH_ENABLED=true` nas variáveis do repositório somente depois
  de validar esse cadastro;
- configure a chave do atualizador Tauri e as credenciais de assinatura das
  plataformas Desktop;
- defina `DESKTOP_PUBLISH_ENABLED=true` somente depois de validar todos os
  segredos exigidos.

Sem essas variáveis, os workflows ainda constroem e validam o que é seguro, mas
registram a distribuição como desativada em vez de tentar um upload incompleto.
