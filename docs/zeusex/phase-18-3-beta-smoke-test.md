# Fase 18.3 — Teste de fumaça isolado da Beta

O comando abaixo inicializa uma instância descartável do ZeusExAI:

```bash
jarvis zeusex beta-smoke
```

O teste valida inicialização do runtime, integridade SQLite, memória persistente e
comandos locais. Ele usa motor de IA desativado, não chama rede, não abre o
microfone e não acessa a pasta real definida em `ZEUSEX_DATA_DIR`.

Ao final, a pasta temporária é removida. Qualquer falha faz o comando retornar
código de saída diferente de zero, permitindo uso em instalação e suporte.
