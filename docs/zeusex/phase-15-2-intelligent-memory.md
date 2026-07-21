# Fase 15.2 — Memória Inteligente

A memória inteligente amplia a memória legada do ZeusExAI sem substituí-la.

## Estrutura

As informações são persistidas na tabela `intelligent_memories`, separada da tabela histórica `memories`. Essa decisão mantém compatibilidade com o OpenJarvis e permite migração gradual.

Cada memória possui:

- categoria;
- conteúdo;
- projeto opcional;
- importância de 1 a 5;
- data de criação;
- data de atualização.

## Categorias iniciais

- `general` — informações gerais;
- `profile` — perfil do usuário;
- `project` — contexto de projetos;
- `product` — produtos acompanhados;
- `campaign` — campanhas;
- `preference` — preferências;
- `decision` — decisões registradas.

## Operações

`IntelligentMemoryStore` oferece:

- `remember()` para registrar informação estruturada;
- `get()` para consultar uma memória por identificador;
- `list()` para filtrar por categoria ou projeto;
- `search()` para localizar conteúdo e projetos.

Resultados são ordenados primeiro pela importância e depois pela recência.

## Segurança e privacidade

- armazenamento local em SQLite;
- nenhuma sincronização externa automática;
- nenhuma informação é enviada a provedores de IA pelo módulo;
- a memória legada permanece operacional;
- exclusão não foi automatizada nesta etapa.

## Próxima integração

A etapa seguinte conectará a memória estruturada ao orquestrador, ao runtime e ao painel móvel, mantendo ações de alteração e exclusão sob controle explícito do usuário.
