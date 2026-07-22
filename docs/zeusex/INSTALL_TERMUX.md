# Instalação do ZeusExAI no Android com Termux

## Escopo atual

O Termux pode executar o núcleo, a CLI, memória, Skills e provedores HTTP do ZeusExAI. A automação de desktop do Windows e os backends de áudio locais podem não funcionar no Android sem adaptações específicas.

## Requisitos

- Termux instalado por uma fonte confiável e atualizada
- Android com espaço livre para Python, Git e dependências
- conexão de rede para instalação inicial

## Instalação básica

```bash
pkg update
pkg upgrade
pkg install python git clang rust
python -m pip install --upgrade pip
git clone https://github.com/Jrdss776/ZeusExAI.git
cd ZeusExAI
git switch develop-zeusex
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Valide:

```bash
jarvis zeusex status
jarvis zeusex diagnose
```

## Uso com Ollama remoto

O Android pode usar uma instância Ollama executada em outro computador da mesma rede:

```bash
export ZEUSEX_AI_PROVIDER=ollama
export ZEUSEX_AI_MODEL=qwen2.5:3b
export ZEUSEX_AI_BASE_URL=http://IP_DO_COMPUTADOR:11434
jarvis zeusex diagnose
```

A instância Ollama precisa aceitar conexões da rede local. Não exponha a porta diretamente à internet.

## Uso com API compatível

```bash
export ZEUSEX_AI_PROVIDER=openai-compatible
export ZEUSEX_AI_MODEL=SEU_MODELO
export ZEUSEX_AI_BASE_URL=https://ENDERECO_DA_API
read -s -p 'Chave da API: ' ZEUSEX_AI_API_KEY
export ZEUSEX_AI_API_KEY
jarvis zeusex diagnose
```

## Voz no Android

Nesta fase, `faster-whisper`, `sounddevice` e `pyttsx3` são considerados opcionais e voltados principalmente ao desktop. No Termux, mantenha:

```bash
export ZEUSEX_VOICE_ENABLED=false
```

O comando de simulação continua disponível:

```bash
jarvis zeusex voice simulate "Zeus status"
```

## Testes focados

```bash
python -m pip install pytest ruff
export PYTHONPATH=src
python -m pytest tests/zeusex -q
ruff check src/openjarvis/zeusex src/openjarvis/cli/zeusex_cmd.py tests/zeusex
```

## Limitações e segurança

- não considere o Termux equivalente a um aplicativo Android nativo;
- não conceda acesso amplo ao armazenamento sem necessidade;
- não salve chaves em scripts versionados;
- recursos de microfone e abertura de aplicativos exigem uma camada Android específica futura;
- comandos falados simulados continuam sujeitos às mesmas confirmações do runtime.
