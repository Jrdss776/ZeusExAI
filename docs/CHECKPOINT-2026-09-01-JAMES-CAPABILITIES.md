# Ponto de retomada — James e capacidades locais

Data: 2026-09-01

## Objetivo

Restaurar organização de pastas, encerramento seguro de programas, diagnóstico
do computador e apoio à programação sem prejudicar a velocidade das conversas
comuns.

## Implementado e salvo

- Roteamento híbrido: conversa comum usa o modo rápido; arquivos, programas,
  manutenção e programação usam o modo agente.
- Ferramentas locais de diagnóstico, processos e prévia de organização.
- Organização sem recursão, exclusão ou sobrescrita, protegida pelo hash da prévia.
- Encerramento normal de programa no Windows, sem força, validando PID e nome.
- Ações mutáveis conectadas ao sino de aprovação do desktop.
- Ferramentas seguras de programação e inspeção conectadas ao James Master.
- Testes do roteamento frontend: 13 aprovados.

## Continuação concluída em 2026-09-02

- Corrigida a listagem de processos no Windows: James usa diretamente a API
  Win32, sem depender do `tasklist.exe`, que estava retornando “Acesso negado”.
- Backend direcionado: 11 testes aprovados e 1 teste opcional ignorado.
- Frontend completo: 46 testes aprovados.
- Interface de produção compilada com sucesso.
- Executável nativo gerado e copiado para
  `releases/openjarvis-desktop-1.0.5-r3.exe`.
- Integridade SHA-256 do `r3`:
  `D0C4920A0CF96F39ED6235FCB9CD2DCFBFDAE7A02D7A27C177F84D5C28A617F7`.
- O atalho `C:\Users\User\Desktop\ZeusExAI.lnk` aponta para a revisão `r3`.
- As versões anteriores foram preservadas e nenhum conhecimento de Excel foi
  removido.

## Correção adicional após validação visual

- Saudações simples agora enviam somente o turno atual, sem reprocessar a
  conversa inteira.
- Perguntas de capacidade como “você pode programar?” usam a rota rápida e
  não acionam o ciclo de ferramentas.
- O contrato local declara explicitamente que James escreve, revisa, depura e
  explica código e que dispõe de ferramentas de programação e manutenção.
- Respostas rápidas locais tiveram o limite de saída reduzido apenas nesses
  casos; pedidos reais de programação continuam usando o modo agente completo.
- Medição direta da saudação com Qwen 2.5 3B: 5,12 segundos, contra os
  aproximadamente 70 segundos observados antes.
- Frontend final: **48 testes aprovados**.

## Revisão r4 — respostas instantâneas

- A validação visual confirmou 19,7 s para saudação e 17,2 s para a pergunta
  de capacidade: melhora importante, porém ainda inadequada para respostas
  determinísticas.
- “Olá James” e perguntas simples como “Você pode programar?” agora são
  respondidas localmente de forma instantânea, sem inferência, sem consumo de
  tokens e sem alterar o modo agente dos pedidos reais.
- Frontend: **49 testes aprovados**.
- Executável: `releases/openjarvis-desktop-1.0.5-r4.exe`.
- SHA-256: `898536880188A36D07639A6428C40ABD31CDA411AD637C9CB33768F0A2C89BDB`.
- O atalho da Área de Trabalho aponta para a revisão `r4`.

## Verificação manual recomendada

1. Confirmar uma conversa curta no modo rápido.
2. Pedir “verifique o estado do meu computador”.
3. Pedir a prévia de organização de uma pasta de teste.
4. Pedir ajuda para revisar um pequeno trecho de código.
