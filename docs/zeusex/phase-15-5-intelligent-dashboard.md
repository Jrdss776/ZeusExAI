# Fase 15.5 — Dashboard Inteligente Unificado

## Objetivo

Consolidar em uma única visão local os dados operacionais e comerciais do ZeusExAI sem duplicar persistência e sem executar ações externas.

## Fontes agregadas

O `IntelligentDashboardService` lê diretamente os armazenamentos existentes:

- projetos e tarefas;
- objetivos e progresso;
- memória inteligente;
- relatórios comerciais;
- modelos de campanha.

Nenhum dado é copiado para uma nova tabela. O snapshot é calculado sob demanda.

## Indicadores

O resumo inclui:

- total e quantidade de projetos ativos;
- tarefas abertas e bloqueadas;
- total de objetivos e objetivos atingidos;
- progresso médio das metas ativas;
- quantidade visível de memórias;
- relatórios comerciais visíveis;
- modelos de campanha visíveis;
- total de alertas.

## Alertas

A primeira versão gera alertas determinísticos para:

- tarefas críticas ou de alta prioridade ainda abertas;
- objetivos ativos com menos de 25% de progresso.

Os alertas são informativos. Eles não alteram tarefas, projetos ou objetivos.

## API local

```text
GET /v1/dashboard?limit=10
```

A resposta contém:

- `summary`;
- `projects`;
- `goals`;
- `priority_tasks`;
- `recent_memories`;
- `top_products`;
- `campaign_templates`;
- `alerts`.

O limite é restringido ao intervalo de 1 a 50 itens por seção.

## Segurança

- rota somente leitura;
- nenhuma rota `DELETE`;
- nenhuma publicação automática;
- nenhuma chamada de marketplace;
- nenhuma credencial no snapshot;
- geração local e sob demanda.

## Próxima fase

A Fase 16 adicionará integrações externas opcionais e autenticadas. O dashboard continuará funcionando integralmente sem essas integrações.
