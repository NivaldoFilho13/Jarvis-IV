# JARVIS-IV

Versão que roda **sem internet e sem créditos de API**. O reconhecimento de
voz é feito localmente no seu PC usando o [Vosk](https://alphacephei.com/vosk/),
e a síntese de voz usa o motor do próprio Windows (SAPI5).

## 1. Instalar o Python

Baixe em https://python.org (marque "Add Python to PATH" na instalação).

## 2. Instalar as dependências

Abra o cmd na pasta dos arquivos e rode:

```
pip install vosk sounddevice pyttsx3 pycaw comtypes keyboard
```

Nenhuma dessas precisa de compilação complicada — diferente da versão antiga,
você **não precisa mais do pyaudio nem do pipwin**.

## 3. Baixar o modelo de voz em português (uma vez só, precisa de internet)

1. Acesse: https://alphacephei.com/vosk/models
2. Baixe um modelo em português. Recomendo:
   - **`vosk-model-small-pt-0.3`** (~40 MB) — leve e rápido, ótimo para comandos curtos.
   - **`vosk-model-pt-fb-v0.1.1-20220516_2113`** (~1.5 GB) — mais preciso, mas usa mais memória.
   - Para começar, use o modelo pequeno.
3. Extraia o `.zip` baixado.
4. Renomeie a pasta extraída para **`modelo_vosk`** e coloque dentro da mesma
   pasta do `chat.py`.

Estrutura final esperada:
```
assistente_voz/
├── chat.py
├── comandos.json
├── README.md
└── modelo_vosk/
    ├── am/
    ├── conf/
    ├── graph/
    └── ...
```

Depois disso, **nunca mais precisa de internet** para o reconhecimento de voz
funcionar — o modelo já está no seu disco.

## 4. Rodar o assistente

Comandos de mídia/volume podem pedir execução como Administrador. Clique
direito no cmd/PowerShell → "Executar como administrador", navegue até a
pasta e rode:

```
python chat.py
```

Você vai ouvir "Assistente de voz offline ativado" — a partir daí, fale.

## 5. Comandos disponíveis

- "abrir bloco de notas", "abrir calculadora", "abrir navegador", "abrir paint"
- "youtube", "google", "gmail" → abre o site (precisa de internet só para a página carregar)
- "pesquisar por [algo]" → pesquisa no Google
- "tocar" / "pausar" → play/pause da mídia
- "próxima música" / "música anterior"
- "aumentar volume" / "diminuir volume" / "mudo" / "desmutar"
- "abrir downloads" → exemplo de comando personalizado
- "sair" → encerra o assistente

## 6. Adicionar seus próprios comandos

Edite o **comandos.json** (não precisa mexer no código):

```json
{
  "programas": {
    "nome que você vai falar": "caminho\\do\\programa.exe"
  },
  "sites": {
    "nome que você vai falar": "https://site.com"
  },
  "personalizados": {
    "nome que você vai falar": "comando de terminal ou caminho para executar"
  }
}
```

## Diferenças em relação à versão com Google (antiga)

| | Versão Google | Versão Vosk (offline) |
|---|---|---|
| Precisa de internet para ouvir comandos | Sim | **Não** |
| Precisa de API/créditos | Não (grátis, mas limitado) | **Não** |
| Precisão do reconhecimento | Mais alta | Boa, um pouco menor (principalmente no modelo pequeno) |
| Primeira configuração | Mais simples | Precisa baixar o modelo (~40 MB a 1.5 GB) uma vez |
| Privacidade | Áudio vai para servidores do Google | **Áudio nunca sai do seu PC** |

Se a precisão do modelo pequeno não for suficiente para o que você precisa,
troque para o modelo maior (`vosk-model-pt-fb-v0.1.1...`) — o código não
muda, só a pasta `modelo_vosk`.

## Observações

- Por segurança, o script **não inclui** comando para desligar/reiniciar o PC
  por padrão. Se quiser adicionar, use em "personalizados":
  `"desligar computador": "shutdown /s /t 5"` — mas tome cuidado, pois qualquer
  ruído parecido pode acionar sem querer.
- Sem "wake word" (palavra de ativação): o assistente sempre tenta interpretar
  o que capta no microfone. Se isso gerar ativações indesejadas em ambiente
  barulhento, me avise que dá pra adicionar uma palavra de ativação.
