# Jarvis_IV

Versão que roda **sem internet e sem créditos de API**. O reconhecimento de
voz é feito localmente no seu PC usando o [Vosk](https://alphacephei.com/vosk/),
e a síntese de voz usa o motor do próprio Windows (SAPI5).

> A única exceção é o comando "pesquisar por..." e abrir sites, que abrem o
> navegador — isso naturalmente precisa de internet para carregar a página,
> mas o assistente em si (ouvir e entender seus comandos) funciona 100% offline.

## 1. Instalar o Python

Baixe em https://python.org (marque "Add Python to PATH" na instalação).

## 2. Instalar as dependências

Abra o cmd na pasta dos arquivos e rode:

```
pip install vosk sounddevice numpy pyttsx3 pycaw comtypes keyboard pywebview
```

Nenhuma dessas precisa de compilação complicada — diferente da versão antiga,
você **não precisa mais do pyaudio nem do pipwin**.

> `pywebview` usa o WebView2 do Windows pra desenhar a janela. Ele já vem
> instalado por padrão no Windows 10/11 atualizados; se der erro relacionado
> a "WebView2" ao abrir a interface, baixe o runtime em
> https://developer.microsoft.com/microsoft-edge/webview2/ (é rápido e grátis).

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
├── interface.html
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

**Comandos gerais do PC:**
- "que horas são" / "que dia é hoje" → fala a hora ou a data atual
- "bloquear tela" → bloqueia o Windows (Win+L)
- "mostrar área de trabalho" / "minimizar tudo" → equivalente a Win+D
- "suspender pc" / "hibernar pc" → coloca o PC pra dormir (não desliga — continua tudo aberto, só "pausa")
- "abrir gerenciador de tarefas" / "abrir painel de controle" / "abrir configurações"
- "tirar print" / "capturar tela" → abre a ferramenta de captura do Windows
- "abrir lixeira" / "esvaziar lixeira"
- "listar microfones" → mostra no terminal os microfones que o Windows enxerga (útil se quiser forçar um específico, veja a seção sobre microfone)

Por segurança, comandos de **desligar/reiniciar** o PC continuam de fora por
padrão (veja o final do README se quiser adicionar).

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

## Melhorando a precisão do reconhecimento

O `chat.py` já vem com duas melhorias que aumentam bastante a precisão:

1. **Reconhecimento restrito por vocabulário**: em vez de tentar entender
   qualquer palavra do português, o assistente só escolhe entre os comandos
   que você tem cadastrados (fixos + os do `comandos.json`). Isso reduz muito
   os erros de transcrição.
2. **Correção aproximada (fuzzy)**: se ele ouvir algo bem parecido com um
   comando (ex.: "abrir bloco de nota" em vez de "abrir bloco de notas"),
   ainda assim executa o comando certo.

Se mesmo assim a precisão não estiver boa o suficiente:
- Troque para o modelo maior (`vosk-model-pt-fb-v0.1.1...`, ~1.5 GB) — ele
  é mais preciso que o pequeno, principalmente com ruído de fundo.
- Fale de forma clara e num ritmo normal (nem muito rápido, nem exagerado),
  a uma distância razoável do microfone.
- Cheque se o Windows está usando o microfone certo como padrão
  (Configurações → Sistema → Som → Entrada).
- Se tiver muito ruído de fundo constante, um microfone com cancelamento de
  ruído (headset) ajuda bastante — o modelo Vosk não faz cancelamento de
  ruído sozinho.

## Sobre a escolha do microfone

O Jarvis agora escolhe o microfone **automaticamente e sem perguntar nada**:
ele sempre usa o dispositivo que o Windows tem como **padrão** no momento.
Isso significa que, se você trocar de microfone (plugar um headset, por
exemplo) e mudar o padrão do Windows, o Jarvis já acompanha sozinho — e
também não trava mais esperando uma resposta quando ele inicia
automaticamente ao ligar o PC.

Se quiser **forçar** um microfone específico (ignorando o que o Windows tem
como padrão), rode o comando "listar microfones" pra ver a lista com os
números, e depois edite `comandos.json` manualmente:

```json
"configuracoes": {
  "microfone_nome": "Headset Bluetooth"
}
```

(`microfone_nome` tem prioridade sobre `microfone_indice` — prefira usar o
nome, já que o número pode mudar entre reinicializações.)

## Se você precisa aproximar muito o microfone pra ele escutar

1. **Ganho de áudio**: por padrão o volume captado é multiplicado por `6.0`
   antes de ir pro reconhecimento. Se ainda estiver fraco, abra o
   `comandos.json` e aumente o valor de `"ganho_audio"` (em
   `"configuracoes"`), por exemplo para `10.0`. Se começar a distorcer ou
   pegar ruído demais, diminua.

2. **Também vale aumentar o microfone no Windows**: clique com o botão
   direito no ícone de som na barra de tarefas → "Configurações de som" →
   "Mais configurações de dispositivo de som" → aba "Gravação" → clique
   duas vezes no seu microfone → aba "Níveis" → suba o volume e, se tiver a
   opção, ative "Impulso de microfone" (Microphone Boost).

Se depois de tudo isso ainda estiver captando fraco, o microfone físico pode
ser o limitador — um headset USB costuma resolver isso de vez.

## Se o Jarvis está cortando a frase no meio (ex.: entende só "abrir")

Isso já vem corrigido: antes, quem decidia quando a frase tinha acabado era
o próprio Vosk (endpointing interno), que às vezes cortava cedo demais. Agora
o próprio Jarvis mede o volume do áudio e só considera a frase completa depois
de um tempo de silêncio de verdade.

Se ainda cortar cedo demais pra você, aumente o `"tempo_silencio_max"` em
`comandos.json` (dentro de `"configuracoes"`) — o padrão é `1.6` segundos.
Tente `2.0` ou `2.5` se você fala mais devagar ou com pausas no meio da
frase. Tem também o `"tempo_max_frase"` (padrão 12 segundos), que é um
limite de segurança pra caso você fique falando sem pausa nenhuma.

## Interface visual

O Jarvis tem uma pequena janela com uma nebulosa de partículas azuis
animadas, que fica escondida por padrão e só aparece quando você pede:

- "mostrar jarvis" / "abrir jarvis" / "abrir interface" → mostra a janela
- "esconder jarvis" / "fechar jarvis" / "fechar interface" → esconde de novo

Enquanto ele está falando, as partículas ficam mais brilhantes e pulsam mais
rápido, **e a janela inteira balança suavemente** (um pequeno vaivém, não é
tremida forte) — dá pra perceber de relance, mesmo com a janela pequena no
canto da tela.

O arquivo `interface.html` controla a aparência das partículas. Se quiser
mudar cores, tamanho ou velocidade, é só editar esse arquivo.

## Iniciar automaticamente com o Windows

Recomendado usar o **Agendador de Tarefas** (não apenas a pasta de
Inicialização), porque dá pra rodar com privilégios altos sem precisar
confirmar o UAC toda vez que o PC ligar:

1. `Win + R` → `taskschd.msc` → Enter
2. "Criar Tarefa..." (não "Criar Tarefa Básica")
3. Aba Geral: dê um nome (ex.: "Jarvis") e marque "Executar com os
   privilégios mais altos"
4. Aba Disparadores → Novo → "Ao fazer logon"
5. Aba Ações → Novo → selecione o `iniciar_assistente.bat`
6. OK, confirme a senha do Windows quando pedir

**Sobre a confiabilidade do áudio nesse cenário:** logo depois do login, o
driver de som do Windows pode levar alguns segundos a mais pra ficar pronto
do que o tempo que a tarefa leva pra iniciar o `chat.py`. Por isso o script
já tenta abrir o microfone várias vezes automaticamente (a cada 3 segundos,
até 20 tentativas) antes de desistir — você não precisa fazer nada, mas se
quiser dar uma folga extra, na aba Disparadores dá pra marcar "Atrasar a
tarefa por" 15 a 30 segundos.

Também: o Jarvis usa automaticamente o microfone padrão do Windows no
momento — não depende mais de lembrar um índice específico, que podia mudar
entre reinicializações. Veja a seção "Sobre a escolha do microfone" acima se
quiser forçar um microfone fixo mesmo assim.

## Orquestrador: Jarvis controlando suas outras IAs (Zez0, Celina, kroga bot...)

O Jarvis agora funciona como um "hub": ele pode acionar suas outras IAs
diretamente, ou executar **fluxos** com várias etapas de uma vez — no
espírito do n8n, mas os "nós" são seus próprios projetos.

### 1. Cadastre cada IA em `integracoes.json`

```json
{
  "ias": {
    "zez0": {
      "tipo": "comando",
      "comando": "python C:\\caminho\\para\\zez0\\principal.py"
    },
    "celina": {
      "tipo": "comando",
      "comando": "python C:\\caminho\\para\\celina\\iniciar.py"
    },
    "kroga": {
      "tipo": "comando",
      "comando": "node C:\\caminho\\para\\kroga-bot\\index.js"
    }
  }
}
```

Os valores que vêm como `"SUBSTITUA_..."` são só um modelo — troque pelo
comando real que você usa hoje pra iniciar cada uma. Se alguma dessas IAs
já expuser algum tipo de API/webhook local, use `"tipo": "webhook"` e um
campo `"url"` no lugar de `"comando"` — o Jarvis manda um POST com a tarefa.

Depois de cadastrado, já dá pra falar ou digitar:
- "iniciar zez0" / "abrir celina" / "rodar kroga"

### 2. Monte fluxos de várias etapas em `fluxos.json`

```json
{
  "fluxos": [
    {
      "nome": "rotina da manhã",
      "gatilho": "rotina da manhã",
      "etapas": [
        {"ia": "zez0", "tarefa": "iniciar"},
        {"ia": "kroga", "tarefa": "enviar resumo do dia"}
      ]
    }
  ]
}
```

O "gatilho" é a frase que você fala ou digita pra acionar o fluxo inteiro
de uma vez — as etapas rodam em ordem, e o Jarvis avisa por voz cada uma.
Isso resolve o "ir pegando cada item um por um": você cria o fluxo uma vez
e depois só dispara ele.

### 3. Comandos digitados, ao mesmo tempo que os falados

O Jarvis agora também lê o que você digita no terminal onde ele está
rodando, ao mesmo tempo que escuta o microfone — dá pra usar os dois sem
precisar escolher um. Isso vale pra qualquer comando (não só fluxos):
digite "abrir calculadora" e aperte Enter, funciona igual a falar.

### Um ponto importante sobre a Celina e o kroga bot

Eu não tenho os detalhes técnicos de como a Celina roda no seu PC nem qual
é o comando exato do kroga bot — então deixei os dois como modelo em
`integracoes.json` pra você preencher com o comando real. Depois de
preenchido, funciona igual ao Zez0.

### Auxílio com outras IAs já feitas

- **Zez0**: agora sei que ele não é um script único — o Pokémon FireRed roda
  via **BizHawk (EmuHawk.exe) + script Lua**, controlando o jogo e lendo
  endereços de memória diretamente, enquanto cobrinha/campo minado/Pac-Man
  provavelmente são scripts Python separados. Por isso troquei o cadastro
  genérico por **uma IA por jogo**: `cobrinha`, `campo minado`, `pacman` e
  `pokemon` — cada um com seu próprio comando em `integracoes.json`. Pra
  `pokemon`, já deixei a estrutura real do comando (EmuHawk + `--lua=` +
  caminho da ROM), só falta você preencher os caminhos. Assim dá pra falar
  "abrir pokemon" ou "iniciar cobrinha" direto, sem ambiguidade sobre qual
  jogo.
- **kroga bot**: sei que ele tem comandos numerados (kroga1 = avisar,
  kroga2 = marcar compromisso, kroga3 = resumo/resposta). Já deixei um
  fluxo de exemplo ("resumo do dia") mandando a tarefa `"kroga3"`. **Atenção:**
  hoje o kroga bot funciona recebendo mensagens pelo WhatsApp — pra esse
  fluxo funcionar de verdade, ele precisa também aceitar comandos vindos de
  fora (por exemplo, uma rota HTTP que o Jarvis chama com `"tipo": "webhook"`
  em vez de `"tipo": "comando"`). Isso exige uma pequena mudança no código
  do kroga bot que eu não fiz aqui, porque não tenho acesso a esse projeto.
  Me chama numa conversa focada no kroga bot se quiser montar essa rota.

## Observações

- Por segurança, o script **não inclui** comando para desligar/reiniciar o PC
  por padrão. 
- Sem "wake word" (palavra de ativação): o assistente sempre tenta interpretar
  o que capta no microfone.
