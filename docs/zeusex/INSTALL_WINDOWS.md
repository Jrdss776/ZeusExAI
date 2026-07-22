# Instalação do ZeusExAI no Windows

## Requisitos

- Windows 10 ou 11 de 64 bits
- Python 3.10, 3.11, 3.12 ou 3.13
- Git
- PowerShell

## Instalação básica

```powershell
git clone https://github.com/Jrdss776/ZeusExAI.git
cd ZeusExAI
git switch main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Valide a instalação:

```powershell
jarvis zeusex status
jarvis zeusex diagnose
```

## Configuração com Ollama

Instale e inicie o Ollama separadamente. Em seguida:

```powershell
$env:ZEUSEX_AI_PROVIDER = "ollama"
$env:ZEUSEX_AI_MODEL = "qwen2.5:3b"
$env:ZEUSEX_AI_BASE_URL = "http://127.0.0.1:11434"
jarvis zeusex diagnose
```

## Voz local opcional

```powershell
python -m pip install -r requirements-zeusex-voice.txt
$env:ZEUSEX_VOICE_ENABLED = "true"
$env:ZEUSEX_VOICE_CAPTURE = "faster-whisper"
$env:ZEUSEX_VOICE_SYNTHESIZER = "pyttsx3"
$env:ZEUSEX_VOICE_LOCALE = "pt-BR"
$env:ZEUSEX_WAKE_WORD = "Zeus"
```

Verifique sem abrir o microfone:

```powershell
jarvis zeusex voice diagnose
jarvis zeusex voice devices
```

Selecione apenas um ID listado:

```powershell
$env:ZEUSEX_VOICE_INPUT_DEVICE = "1"
jarvis zeusex voice listen
```

## Testes focados

```powershell
python -m pip install pytest ruff
$env:PYTHONPATH = "src"
python -m pytest tests/zeusex -q
ruff check src/openjarvis/zeusex src/openjarvis/cli/zeusex_cmd.py tests/zeusex
```

## Segurança

- não grave chaves de API em arquivos versionados;
- o microfone só é acessado por `voice listen`;
- ações de desktop sensíveis continuam exigindo confirmação;
- mantenha o PR em rascunho enquanto CI e testes locais não estiverem estáveis.
