# Assistente de voz "Claude" (local)

Script Python que fica ouvindo o microfone e, quando você diz **"Claude"**,
envia o restante do que você falou para a API da Anthropic e fala a
resposta em voz alta.

## 1. Instalar o Python

Baixe em https://www.python.org/downloads/ (marque "Add Python to PATH"
durante a instalação). Versão recomendada: 3.10 ou superior.

## 2. Instalar as dependências

Abra o terminal (PowerShell ou CMD) na pasta do projeto e rode:

```bash
pip install -r requirements.txt
```

**No Windows, o PyAudio pode falhar ao instalar direto pelo pip.**
Se der erro, instale com:

```bash
pip install pipwin
pipwin install pyaudio
```

## 3. Configurar sua chave de API

1. Copie o arquivo `.env.example` e renomeie a cópia para `.env`.
2. Abra `.env` e cole sua chave da Anthropic (gerada em
   https://console.anthropic.com/ → API Keys → Create Key).

```
ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
```

## 4. Rodar o assistente

```bash
python assistant.py
```

O terminal vai mostrar "Pronto." — a partir daí, fale algo como:

> "Claude, me fale sobre o clima."

O script transcreve, detecta a palavra "Claude", envia o resto da frase
para a API e fala a resposta em voz alta.

Para encerrar, pressione `Ctrl+C` no terminal.

## Observações

- O reconhecimento de voz usado (`speech_recognition` com o serviço do
  Google) precisa de **internet** para funcionar.
- A qualidade da detecção da palavra "Claude" depende do microfone e do
  ruído do ambiente — em local silencioso funciona melhor.
- Cada pergunta que você faz gera uma chamada à API da Anthropic, que é
  paga conforme o uso da sua conta (veja preços em
  https://www.anthropic.com/pricing).
- Se quiser trocar a palavra de ativação, edite `WAKE_WORD` no `.env`
  (ex: `WAKE_WORD=assistente`).
- O histórico de conversa é mantido apenas durante a execução do script
  (é apagado quando você fecha o terminal).
