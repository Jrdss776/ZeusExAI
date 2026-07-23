# Arquitetura do ZeusExAI

O ZeusExAI é uma distribuição personalizada baseada no OpenJarvis, orientada a assistente pessoal local, automação segura e operações comerciais em marketplaces.

## Princípios

1. **Local-first**: executar localmente sempre que viável e recorrer à nuvem apenas quando necessário.
2. **Modularidade**: cada domínio funcional deve ser isolado em módulos ou skills.
3. **Segurança por confirmação**: ações destrutivas, financeiras, publicações e envios exigem confirmação explícita.
4. **Português como padrão**: interface, respostas e documentação do ZeusExAI priorizam pt-BR.
5. **Compatibilidade upstream**: evitar alterações invasivas no núcleo para facilitar futuras atualizações do OpenJarvis.

## Camadas

```text
ZeusExAI
├── Core IA
├── Interface
├── Voz
├── Memória
├── Ferramentas
├── Marketplace
│   ├── Shopee
│   ├── Mercado Livre
│   └── Amazon (futuro)
├── Automação
│   ├── Windows
│   ├── Android
│   └── Navegador
├── Visão
├── Programação
└── Plugins
```

## Responsabilidades

### Core IA
Orquestra modelos, agentes, contexto, ferramentas e políticas de execução.

### Interface
Fornece experiência desktop e futura experiência móvel com identidade visual ZeusExAI.

### Voz
Inclui reconhecimento de fala, palavra de ativação, síntese de voz e controle de escuta.

### Memória
Armazena preferências, histórico útil, tarefas e contexto persistente com regras de privacidade.

### Ferramentas
Disponibiliza utilitários genéricos: arquivos, agenda, pesquisa, cálculos, documentos e integrações.

### Marketplace
Concentra recursos comerciais como pesquisa de produtos, comparação, margem, comissão, títulos, descrições e monitoramento.

### Automação
Executa ações no Windows, Android e navegador com níveis de permissão e confirmação.

### Visão
Analisa imagens, capturas de tela, interfaces, erros e materiais de produtos.

### Programação
Apoia desenvolvimento, testes, GitHub, análise de código e manutenção do próprio ZeusExAI.

### Plugins
Permite extensões desacopladas e skills instaláveis sem modificar o núcleo.

## Níveis de permissão

- **Nível 1 — Consulta**: leitura, pesquisa e análise.
- **Nível 2 — Ação local simples**: abrir aplicativos, navegar em pastas e ajustar preferências reversíveis.
- **Nível 3 — Alteração de dados**: criar, editar, mover ou excluir arquivos.
- **Nível 4 — Execução avançada**: shell, scripts, instalação e mudanças de sistema.
- **Nível 5 — Ação externa sensível**: publicar, comprar, enviar mensagens, operar contas ou realizar transações.

Níveis 3, 4 e 5 devem exigir confirmação conforme contexto e política configurada.

## Roadmap inicial

### Fase 1 — Fundação
- identidade ZeusExAI;
- configuração própria;
- persona em português;
- documentação da arquitetura;
- branch de desenvolvimento.

### Fase 2 — Voz e interface
- palavra de ativação “Zeus”;
- voz pt-BR;
- interface personalizada;
- status de sistema e modos operacionais.

### Fase 3 — Automação do computador
- aplicativos;
- arquivos;
- controles do Windows;
- leitura de tela;
- política de confirmações.

### Fase 4 — Marketplace
- Shopee;
- Mercado Livre;
- análise de produto;
- margem e comissão;
- geração de anúncios.

### Fase 5 — Inteligência pessoal
- memória;
- agenda;
- lembretes;
- monitoramento;
- integração Android.

## Estratégia de desenvolvimento

A branch `main` permanece estável e é a referência para instalação e atualização.
Novas alterações devem ser desenvolvidas em branches de trabalho curtas, organizadas
em commits pequenos e revisáveis, e integradas por pull request. Novas funcionalidades
devem preferir configuração, extensão e skills antes de alterações profundas no núcleo
original.
