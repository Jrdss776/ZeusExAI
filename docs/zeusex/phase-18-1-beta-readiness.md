# Fase 18.1 — Diagnóstico de prontidão para Beta

O comando abaixo verifica localmente os requisitos mínimos antes dos testes da
primeira Beta:

```bash
jarvis zeusex beta-readiness
```

São avaliados Python 3.10–3.13, acesso à pasta de dados e configuração do motor
de IA. O token do painel móvel e a voz são tratados como recursos opcionais e
geram avisos quando ainda não estão configurados.

O diagnóstico não abre o microfone, não chama provedores, não cria bancos e não
mostra chaves. A saída termina com `APROVADA` quando não existem bloqueios e usa
código de saída diferente de zero quando a instalação ainda não está pronta.
