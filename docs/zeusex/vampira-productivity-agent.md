# Vampira — agente leve de e-mail, agenda e tarefas

## Arquitetura

A Vampira é um agente gerenciado do ZeusExAI. Ela não cria um segundo cliente
OpenAI: por padrão, herda o mesmo `engine` e o mesmo modelo que o servidor já
carregou para o James. Uma configuração `model` no próprio agente continua
sendo uma substituição explícita.

O template `vampira_productivity` usa execução manual, até quatro turnos, saída
curta e nenhum tool habilitado por padrão. Isso mantém o consumo de RAM baixo e
impede ações externas até que conectores sejam autorizados deliberadamente.

## Variáveis de ambiente

Nenhuma `OPENAI_API_KEY` adicional é necessária para a Vampira. Configure o
provider/modelo normal do servidor ZeusExAI e ela o reutilizará. O runtime
ZeusExAI isolado continua aceitando, quando usado diretamente:

| Variável | Finalidade |
| --- | --- |
| `ZEUSEX_AI_PROVIDER` | `ollama`, `openai-compatible` ou `disabled` |
| `ZEUSEX_AI_MODEL` | Modelo usado pelo runtime isolado |
| `ZEUSEX_AI_BASE_URL` | Endpoint local ou compatível com OpenAI |
| `ZEUSEX_AI_API_KEY` | Chave do endpoint compatível, somente quando necessária |
| `ZEUSEX_AI_TIMEOUT` | Timeout em segundos |
| `ZEUSEX_DATA_DIR` | Banco e dados locais do ZeusExAI |
| `ZEUSEX_VAMPIRA_AUDIT_LOG` | Caminho recomendado para o JSONL de auditoria ao conectar os serviços |

Não grave chaves ou tokens no repositório. A auditoria registra somente ação,
decisão, motivo e identificador; assunto e corpo de e-mails e conteúdo de
tarefas não são gravados.

## Políticas de segurança

- Leitura, busca, resumo, triagem e prévias podem ser liberados por integração.
- Enviar e-mail, criar compromisso, concluir tarefa ou excluir tarefa exige
  confirmação explícita e específica no momento da ação.
- Exclusão de e-mail e alteração/cancelamento de compromissos ainda não são
  expostos pelos módulos leves da Vampira; portanto não podem ocorrer
  automaticamente. Quando forem adicionados, devem usar a mesma barreira de
  confirmação e auditoria.

## Próximos passos para OAuth Google

1. No Google Cloud Console, crie um cliente OAuth 2.0 do tipo aplicativo para
   computador e habilite Gmail API, Google Calendar API e Google Tasks API.
2. Na tela **Data Sources**, conecte o Google e conclua o consentimento no
   navegador. O fluxo existente salva as credenciais fora do repositório, em
   `~/.openjarvis/connectors/google.json`.
3. Comece com escopos somente leitura. Amplie permissões apenas quando houver
   uma ação concreta e mantenha confirmação explícita para qualquer escrita.
4. Injete `JsonlProductivityAudit` nos serviços ao habilitar as escritas e use
   o caminho de `ZEUSEX_VAMPIRA_AUDIT_LOG`.
5. Teste primeiro listagem, resumo, agenda e tarefas em modo de leitura; depois
   teste prévias e confirme uma única ação controlada.

## Teste local

```powershell
python -m pytest tests/agents/test_executor.py tests/agents/test_template_prompts.py tests/server/test_agent_manager_routes.py tests/zeusex/test_gmail.py tests/zeusex/test_google_calendar.py tests/zeusex/test_productivity_tasks.py -q
cd frontend
npm run build
```
