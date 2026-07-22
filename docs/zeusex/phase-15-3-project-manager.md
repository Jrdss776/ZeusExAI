# Fase 15.3 — Gerenciador de Projetos

A Fase 15.3 adiciona gerenciamento local e persistente de projetos ao ZeusExAI.

## Componentes

- `ProjectStore`: projetos e tarefas em SQLite.
- `ProjectService`: integra projetos à memória inteligente.
- `ProjectAPIService`: camada JSON local.
- domínio `project` no orquestrador central.

## Projetos

Cada projeto contém:

- nome único;
- descrição;
- objetivo;
- status;
- datas de criação e atualização.

Status permitidos:

- `planned`;
- `active`;
- `paused`;
- `completed`;
- `archived`.

## Tarefas

Cada tarefa pertence a um projeto e contém:

- título;
- descrição;
- status;
- prioridade;
- vencimento opcional;
- datas de criação e atualização.

Status permitidos:

- `backlog`;
- `todo`;
- `in_progress`;
- `blocked`;
- `done`.

Prioridades permitidas:

- `low`;
- `medium`;
- `high`;
- `critical`.

## Memória inteligente

A criação de um projeto registra uma memória da categoria `project`.

Tarefas de prioridade alta ou crítica também são registradas como contexto do projeto. Decisões podem ser registradas explicitamente na categoria `decision`.

## API local

Rotas implementadas:

- `GET /v1/projects`;
- `POST /v1/projects`;
- `GET /v1/projects/{id}`;
- `PATCH /v1/projects/{id}/status`;
- `GET /v1/projects/{id}/tasks`;
- `POST /v1/projects/{id}/tasks`;
- `PATCH /v1/tasks/{id}/status`;
- `POST /v1/projects/{id}/decisions`.

Não existe rota de exclusão automática nesta fase.

## Orquestração

O domínio `project` reconhece comandos como:

- criar projeto;
- listar projetos;
- adicionar tarefa;
- tarefas do projeto;
- status do projeto;
- decisão do projeto.

## Segurança

- persistência somente local em SQLite;
- nenhuma publicação externa;
- nenhuma exclusão automática;
- alterações de status explícitas;
- nomes de projetos protegidos contra duplicidade sem diferenciar maiúsculas e minúsculas.

## Próxima etapa

A Fase 15.4 adicionará objetivos mensuráveis, indicadores de progresso e associação de metas aos projetos.
