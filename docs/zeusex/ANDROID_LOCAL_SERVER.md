# Servidor local ZeusEXai no Android/Termux

## Estado atual

O ZeusEXai inclui um servidor HTTP opcional para a futura interface Android. Ele:

- inicia somente por comando explícito;
- aceita apenas endereços de loopback;
- usa `127.0.0.1` por padrão;
- rejeita `0.0.0.0`, IP da rede local e exposição externa;
- exige token Bearer para rotas protegidas;
- mantém o token somente em memória;
- não oferece publicação, compras, mensagens ou shell;
- inclui um painel web local que não grava o token no navegador.

## Preparação no Termux

```bash
pkg update
pkg install python git
git clone https://github.com/Jrdss776/ZeusExAI.git
cd ZeusExAI
git switch develop-zeusex
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Crie um token apenas para a sessão atual:

```bash
read -s -p "Token local: " ZEUSEX_MOBILE_API_TOKEN
export ZEUSEX_MOBILE_API_TOKEN
```

O token precisa ter ao menos 16 caracteres.

## Iniciar manualmente

```bash
jarvis zeusex mobile-serve --port 8765
```

No mesmo aparelho, abra:

```text
http://127.0.0.1:8765
```

Para encerrar, volte ao Termux e pressione `Ctrl+C`.

## Limites de segurança

- não redirecione a porta para a internet;
- não use aplicativos de túnel;
- não salve o token em scripts versionados;
- não altere o host para um IP externo;
- o painel é uma fundação local, não um aplicativo Android nativo final.


## Instalar o painel como PWA

Com o servidor em execução, abra `http://127.0.0.1:8765` no navegador do
mesmo aparelho. Quando o navegador oferecer a opção, escolha **Instalar
aplicativo** ou **Adicionar à tela inicial**.

A PWA:

- usa manifesto e ícone servidos pelo próprio ZeusEXai;
- funciona em modo visual independente quando o navegador oferecer suporte;
- armazena em cache somente a estrutura visual;
- nunca armazena respostas de `/v1`, relatórios ou o token;
- continua dependendo do Termux e do servidor local em execução.

Se o servidor estiver desligado, a tela pode abrir com a estrutura visual em
cache, mas análises, campanhas, agenda e fila permanecerão indisponíveis.
