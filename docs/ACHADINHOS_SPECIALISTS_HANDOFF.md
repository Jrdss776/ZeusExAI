# Retomada — Orquestrador de especialistas do Achadinhos do JR

Atualizado em 31 de julho de 2026.

## Arquitetura aprovada

O Jarvis coordena sete funções separadas:

1. Coletor de evidências;
2. Analista de produto;
3. Analista de concorrência;
4. Estrategista de vendas;
5. Criador de anúncios;
6. Criador de roteiros;
7. Revisor independente.

Somente o Coletor pesquisa. Os outros especialistas recebem a ficha aprovada
pelo usuário e precisam vincular cada afirmação factual aos campos e URLs dessa
ficha. Hipóteses comerciais permanecem identificadas como hipóteses.

## Implementado

- Fluxo em duas etapas: coleta e revisão da ficha antes da execução dos bots;
- `POST /v1/commercial/collect` para criar a ficha verificável;
- `POST /v1/commercial/orchestrate` para executar somente a ficha aprovada;
- Especialistas selecionados conforme a ação comercial;
- Revisor independente executado ao final de cada fluxo;
- Bloqueio de fontes inventadas, campos inexistentes e ficha sem evidência;
- Respostas estruturadas em JSON e falha segura quando o formato é inválido;
- Modelo configurável por função, com retorno automático ao modelo principal;
- Uso automático de `openrouter/openrouter/free` para todas as funções quando
  a chave do OpenRouter estiver disponível;
- Registro do modelo realmente usado na ficha e em cada saída;
- Reutilização das fontes pesquisadas quando há troca para o modelo de retorno;
- Interface em português para revisar fatos, fontes, alertas e campos ausentes;
- Opção antiga **Preparar no chat** preservada como alternativa.

## Configuração dos modelos

O modelo ativo do ZeusExAI é sempre o retorno padrão. Cada variável abaixo é
opcional; quando estiver vazia, a função usa o modelo ativo:

- `ZEUSEX_COMMERCIAL_COLLECTOR_MODEL`;
- `ZEUSEX_COMMERCIAL_PRODUCT_ANALYST_MODEL`;
- `ZEUSEX_COMMERCIAL_COMPETITOR_ANALYST_MODEL`;
- `ZEUSEX_COMMERCIAL_SALES_STRATEGIST_MODEL`;
- `ZEUSEX_COMMERCIAL_LISTING_WRITER_MODEL`;
- `ZEUSEX_COMMERCIAL_VIDEO_WRITER_MODEL`;
- `ZEUSEX_COMMERCIAL_REVIEWER_MODEL`.

Os identificadores precisam ser compatíveis com o motor já configurado. As
chaves dos provedores continuam no mecanismo de credenciais existente; nenhuma
chave é armazenada no código comercial.

## Validação concluída

- 47 testes comerciais Python aprovados;
- 12 testes da interface aprovados;
- Compilação de produção da interface aprovada;
- Verificação estática dos novos arquivos Python aprovada;
- Inspeção visual da Central Comercial em desktop aprovada após corrigir a
  quebra dos ícones no título;
- Casos cobertos: dados insuficientes, fonte inventada, métrica inexistente,
  JSON inválido, provedor preferido indisponível e retorno ao modelo local.

## Pendente antes de publicar

- Teste real com um produto e credenciais do provedor escolhido;
- Definição dos modelos externos a usar em cada função;
- Ajuste responsivo da barra lateral geral do aplicativo para telas de celular;
- Revisão final das alterações;
- Commit, envio ao GitHub e pull request após aprovação.

## Local de trabalho

- Repositório: `Jrdss776/ZeusExAI`;
- Cópia de desenvolvimento:
  `C:\Users\User\.codex\visualizations\2026\07\30\019fb516-7ccf-7561-bdf6-23288b8cc623\ZeusExAI`;
- Branch: `codex/achadinhos-specialist-orchestrator`.
