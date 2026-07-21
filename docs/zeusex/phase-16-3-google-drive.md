# Fase 16.3 — Fundação somente-leitura do Google Drive

Esta fase adiciona contratos locais para futura integração com Google Drive sem
OAuth, SDK obrigatório ou persistência de credenciais no núcleo.

## Escopo

- integração desativada por padrão;
- modo único `metadata_read`;
- pesquisa limitada de arquivos;
- consulta de metadados por identificador;
- estado sanitizado do conector.

```text
GET /v1/integrations/google-drive/status
GET /v1/integrations/google-drive/files
GET /v1/integrations/google-drive/files/{id}
```

O módulo não baixa conteúdo, cria pastas, envia arquivos, compartilha, move,
renomeia, edita ou exclui itens. Identificadores e consultas são validados antes
de chegar ao conector fornecido pela aplicação hospedeira.

## Próximos passos

1. adaptador OAuth opcional em pacote separado;
2. armazenamento de credenciais pelo sistema operacional;
3. pesquisa visual de metadados no painel móvel;
4. pré-visualização explícita antes de qualquer download futuro;
5. política separada para upload, compartilhamento e exclusão.
