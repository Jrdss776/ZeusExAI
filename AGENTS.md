# AGENTS.md — ZeusExAI

## PROJECT IDENTITY GATE — obrigatório antes de qualquer edição

Este repositório é o **ZeusExAI**, não o projeto `jarvis` multi-brain.

- Raiz esperada: `C:\Users\User\Downloads\GitHub\ZeusExAI`
- Origin esperado: `https://github.com/Jrdss776/ZeusExAI.git`
- O projeto diferente chamado `jarvis` está em
  `C:\Users\User\Downloads\GitHub\jarvis` e usa o origin
  `https://github.com/pguilp25/jarvis.git`.

Antes da primeira escrita em toda tarefa:

1. Execute `git rev-parse --show-toplevel`.
2. Execute `git remote get-url origin`.
3. Compare os dois resultados com os valores esperados acima.
4. Se qualquer valor divergir, pare sem editar e informe o usuário.

Se o pedido mencionar JARVIS multi-brain, `core/prompts_v8.py`, SWE-bench ou o
pipeline UNDERSTAND → PLAN → IMPLEMENT → REVIEW, ele provavelmente pertence ao
repositório irmão `jarvis`; pare antes de editar. Se mencionar Zeus, ZeusExAI,
o aplicativo desktop instalado, `openjarvis.zeusex`, Central Comercial ou os
módulos em `src/openjarvis/zeusex`, permaneça neste repositório.

Não copie integrações ou arquivos entre os dois projetos sem inspecionar antes
a arquitetura nativa do destino e receber orientação explícita do usuário.

## Regras de trabalho

- Preserve alterações locais e não relacionadas do usuário.
- Faça diagnóstico somente leitura antes de implementar correções.
- Para mudanças, adicione ou ajuste testes e execute a suíte relevante.
- Para o ZeusExAI Beta, prefira os comandos e runbooks em `docs/zeusex/`.
- O executável instalado e o repositório fonte são artefatos diferentes; confirme
  qual deles o usuário está usando antes de corrigir inicialização.
- Integrações Google, Gmail, Calendar e Telegram já possuem contratos próprios no
  ZeusExAI. Não crie clientes paralelos antes de auditar esses módulos.
