# Fase 17.4 — Políticas de execução e auditoria

A Fase 17.4 adiciona governança ao executor local da Fase 17.3 sem ampliar suas permissões.

## Políticas por ação

Cada ação local possui limites declarativos:

- tentativas máximas por plano;
- execuções máximas por hora;
- tamanho máximo do argumento;
- timeout lógico;
- nome de ação normalizado.

Políticas padrão:

- `system.information`: até 3 tentativas por plano, 30 execuções por hora, timeout lógico de 2 segundos e nenhum argumento;
- `filesystem.list_directory`: até 5 tentativas por plano, 20 execuções por hora, timeout lógico de 5 segundos e argumento de até 2048 caracteres.

## Auditoria

Toda solicitação produz eventos persistidos em SQLite. Eventos possíveis:

- `attempt`;
- `blocked`;
- `failed`;
- `timeout`;
- `completed`.

Cada evento contém plano, ação, decisão, motivo, duração e data UTC. Tokens, credenciais e conteúdo privado não fazem parte do registro.

## Timeout lógico

O timeout é verificado após o retorno do handler. Ele sinaliza que a política foi excedida, mas não encerra processos. Isso é intencional: o executor não cria subprocessos, não executa shell e não possui ações externas.

## Garantias preservadas

- apenas ações locais registradas;
- plano aprovado e confirmação explícita continuam obrigatórios;
- idempotência permanece aplicada pelo executor base;
- Gmail, Calendar, Drive, GitHub, WhatsApp, Telegram, Slack, HTTP, shell e subprocessos continuam bloqueados;
- a auditoria não habilita execução externa.

## Arquivos

- `src/openjarvis/zeusex/execution_policy.py`
- `src/openjarvis/zeusex/execution_audit.py`
- `src/openjarvis/zeusex/policy_controlled_executor.py`
- `tests/zeusex/test_execution_policy.py`
