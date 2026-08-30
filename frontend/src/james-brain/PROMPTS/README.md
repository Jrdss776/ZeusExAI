# Prompts e habilidades

As habilidades executáveis do James permanecem no registro tipado `frontend/src/lib/jamesIntelligence.ts`.

Elas são selecionadas conforme o pedido atual e não são todas inseridas em todas as conversas. Esta pasta documenta a arquitetura, mas não mantém uma segunda cópia das instruções para evitar divergência.

Ao criar uma nova habilidade:

1. Dê a ela um identificador estável.
2. Defina gatilhos específicos, evitando correspondências genéricas.
3. Escreva instruções curtas e verificáveis.
4. Marque quando exigir confirmação.
5. Adicione testes de seleção e de não seleção.
