# Fase 19.1 — Gate de prontidão para versão estável

A Fase 19.1 transforma a estabilização da Beta em um processo verificável. O
comando não consulta serviços externos, não coleta telemetria e não presume que
uma plataforma foi validada. Todas as evidências precisam ser informadas por quem
conduziu os testes.

## Critérios mínimos

- sete dias de observação da Beta publicada;
- duas execuções completas e aprovadas de `beta-acceptance`;
- instalação real validada no Windows;
- instalação real validada no Android/Termux;
- zero bugs críticos abertos.

## Uso

```powershell
jarvis zeusex stable-readiness `
  --beta-days 7 `
  --acceptance-runs 2 `
  --platform windows `
  --platform android `
  --open-critical-bugs 0
```

Qualquer evidência ausente produz um bloqueio e código de saída diferente de
zero. A versão estável não deve ser criada enquanto o resultado não for
`Prontidão Estável: APROVADA`.

## Limites

O comando não substitui testes, revisão de bugs ou validação humana. Contagens e
plataformas informadas devem corresponder a evidências reais registradas durante
o ciclo da Beta.
