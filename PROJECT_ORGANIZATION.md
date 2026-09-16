# ZeusExAI / James — organização do projeto

Esta é a pasta principal e ativa do ZeusExAI/James.

Localização oficial no Windows: `C:\Users\User\Documents\ZeusExAI`.

## Estrutura

- `frontend/` — interface React/Tauri, incluindo o HUD do James.
- `src/` — código principal Python e serviços do OpenJarvis/ZeusExAI.
- `desktop/` — integração e recursos do aplicativo desktop.
- `rust/` — componentes nativos em Rust.
- `configs/` — configurações versionadas do sistema.
- `assets/` — imagens e recursos permanentes.
- `tests/` — testes automatizados do projeto atual.
- `docs/` — documentação técnica.
- `scripts/`, `tools/`, `deploy/` e `examples/` — automação, utilitários, implantação e exemplos.
- `releases/` — executável e instaladores preservados.
- `archive/` — materiais históricos preservados, mas não carregados pelo projeto atual.

## Materiais históricos

`archive/commercial-modules/` contém sete módulos comerciais encontrados somente em uma cópia antiga.

`archive/beta-data/` contém bancos de dados da versão beta. Esses arquivos não fazem parte do funcionamento normal da versão atual.

## Dependências e arquivos recriáveis

`frontend/node_modules/` permanece disponível para desenvolver e recompilar a interface.

Os diretórios `frontend/dist/` e `frontend/src-tauri/target/` são gerados por compilação e podem ser recriados quando necessário.

## Regra de manutenção

Mantenha o trabalho ativo nesta pasta. Não copie versões completas do projeto para outras pastas; para entregas, use `releases/`, e para materiais antigos que ainda precisem ser preservados, use `archive/`.
