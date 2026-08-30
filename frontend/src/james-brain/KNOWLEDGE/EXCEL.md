# Excel — referência operacional

- Proprietário: James / ZeuxExAI
- Escopo: análise, organização e alteração segura de planilhas
- Revisado em: 2026-08-29

## Antes de trabalhar

1. Identifique o formato: `.xlsx` preserva fórmulas e estilos; `.xlsm` pode conter macros; `.csv` guarda apenas uma tabela sem fórmulas, formatação ou múltiplas abas.
2. Confirme o objetivo, as abas e colunas envolvidas. Não suponha o significado de cabeçalhos ambíguos.
3. Detecte idioma e localidade do arquivo antes de escrever fórmulas. Nomes de funções, separador de argumentos, datas e decimais podem variar.
4. Preserve o arquivo original quando a alteração puder remover fórmulas, macros, validações ou formatação.

## Escolha da solução

- Use Tabelas do Excel para dados estruturados, referências legíveis e expansão automática.
- Para agregações condicionais, prefira `SOMASES`/`CONT.SES` (`SUMIFS`/`COUNTIFS`).
- Para buscas, prefira `PROCX` (`XLOOKUP`) quando disponível; use `ÍNDICE` + `CORRESP` para compatibilidade. Evite `PROCV` com índice de coluna frágil quando a estrutura puder mudar.
- Use `FILTRAR`, `CLASSIFICAR` e `ÚNICO` (`FILTER`, `SORT`, `UNIQUE`) quando matrizes dinâmicas forem compatíveis com a versão do Excel.
- Use Tabela Dinâmica para exploração e resumo interativo; use Power Query para importação, limpeza e transformação repetível de dados.
- Use VBA somente quando fórmulas, Tabelas, Power Query ou automação externa não resolverem o problema com menor risco.

## Qualidade dos dados

- Diferencie vazio, zero e texto vazio; eles podem produzir resultados diferentes.
- Preserve identificadores com zeros à esquerda como texto.
- Normalize datas, moedas e percentuais antes de calcular.
- Evite números fixos escondidos em fórmulas; coloque parâmetros em células nomeadas ou tabelas de configuração.
- Trate erros com intenção. `SEERRO` (`IFERROR`) não deve ocultar problemas de origem sem diagnóstico.

## Validação obrigatória

- Verifique fórmulas em casos normais, vazios, duplicados, valores ausentes e limites.
- Compare totais e quantidade de linhas antes e depois da transformação.
- Confirme que referências, filtros, validações, formatos e macros foram preservados.
- Ao entregar uma alteração, informe o que mudou, onde mudou e como conferir o resultado.
