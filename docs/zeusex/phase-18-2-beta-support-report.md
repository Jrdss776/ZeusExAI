# Fase 18.2 — Relatório sanitizado de suporte Beta

O relatório reúne diagnóstico de prontidão, sistema operacional e versão do
Python para ajudar nos testes da Beta:

```bash
jarvis zeusex beta-report --output zeusex-beta-report.json
```

O arquivo não inclui variáveis de ambiente, caminhos de credenciais, tokens ou
chaves. A gravação é atômica, exige extensão `.json` e não substitui um relatório
existente sem a opção `--replace`.

O comando não acessa rede, microfone ou provedores externos. O usuário pode abrir
e revisar o JSON antes de compartilhá-lo com o suporte.
