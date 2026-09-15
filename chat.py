import difflib
import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from datetime import datetime

import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

import webview

import pyttsx3
import keyboard

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

PASTA_BASE = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(PASTA_BASE, "comandos.json")
MODELO_PATH = os.path.join(PASTA_BASE, "modelo_vosk")
INTERFACE_PATH = os.path.join(PASTA_BASE, "interface.html")
INTEGRACOES_PATH = os.path.join(PASTA_BASE, "integracoes.json")
FLUXOS_PATH = os.path.join(PASTA_BASE, "fluxos.json")

TAXA_AMOSTRAGEM = 16000

JANELA = None
INTEGRACOES = {}
FLUXOS = {}


def carregar_config():
    if not os.path.exists(CONFIG_PATH):
        padrao = {
            "programas": {
                "bloco de notas": "notepad.exe",
                "calculadora": "calc.exe",
                "navegador": "chrome.exe",
                "explorador de arquivos": "explorer.exe",
                "paint": "mspaint.exe",
            },
            "sites": {
                "youtube": "https://youtube.com",
                "google": "https://google.com",
                "gmail": "https://mail.google.com",
            },
            "personalizados": {
                "abrir downloads": f"explorer.exe {os.path.join(os.path.expanduser('~'), 'Downloads')}"
            },
            "configuracoes": {
                "microfone_indice": None,
                "microfone_nome": None,
                "ganho_audio": 6.0,
                "tempo_silencio_max": 1.6,
                "tempo_max_frase": 12,
            },
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(padrao, f, ensure_ascii=False, indent=2)
        return padrao

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    config.setdefault("configuracoes", {})
    config["configuracoes"].setdefault("microfone_indice", None)
    config["configuracoes"].setdefault("microfone_nome", None)
    config["configuracoes"].setdefault("ganho_audio", 6.0)
    config["configuracoes"].setdefault("tempo_silencio_max", 1.6)
    config["configuracoes"].setdefault("tempo_max_frase", 12)
    return config


def salvar_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


motor_voz = pyttsx3.init()
motor_voz.setProperty("rate", 175)

for voz in motor_voz.getProperty("voices"):
    if (
        "brazil" in voz.name.lower()
        or "portuguese" in voz.name.lower()
        or "pt" in voz.id.lower()
    ):
        motor_voz.setProperty("voice", voz.id)
        break


def falar(texto):
    print(f"[Assistente] {texto}")
    if JANELA is not None:
        try:
            JANELA.evaluate_js("iniciarFala()")
        except Exception:
            pass
    thread_balanco = _iniciar_balanco_janela()
    motor_voz.say(texto)
    motor_voz.runAndWait()
    _parar_balanco_janela(thread_balanco)
    if JANELA is not None:
        try:
            JANELA.evaluate_js("pararFala()")
        except Exception:
            pass


def _iniciar_balanco_janela():
    if JANELA is None:
        return None
    try:
        x0, y0 = JANELA.x, JANELA.y
    except Exception:
        return None

    parar = threading.Event()

    def balancar():
        inicio = time.time()
        while not parar.is_set():
            deslocamento_x = int(5 * math.sin((time.time() - inicio) * 9))
            deslocamento_y = int(3 * math.cos((time.time() - inicio) * 7))
            try:
                JANELA.move(x0 + deslocamento_x, y0 + deslocamento_y)
            except Exception:
                break
            time.sleep(0.04)
        try:
            JANELA.move(x0, y0)
        except Exception:
            pass

    thread = threading.Thread(target=balancar, daemon=True)
    thread.start()
    return (thread, parar)


def _parar_balanco_janela(dados_thread):
    if not dados_thread:
        return
    thread, parar = dados_thread
    parar.set()
    thread.join(timeout=1)


def mostrar_icone(categoria):
    if JANELA is not None:
        try:
            JANELA.evaluate_js(f"mostrarIcone('{categoria}')")
        except Exception:
            pass


def saudacao_por_horario():
    hora = datetime.now().hour
    if 5 <= hora < 12:
        return "Bom dia"
    if 12 <= hora < 18:
        return "Boa tarde"
    return "Boa noite"


def _volume_interface():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(interface, POINTER(IAudioEndpointVolume))


def ajustar_volume(delta):
    vol = _volume_interface()
    atual = vol.GetMasterVolumeLevelScalar()
    novo = min(1.0, max(0.0, atual + delta))
    vol.SetMasterVolumeLevelScalar(novo, None)


def mudo(ativar=True):
    vol = _volume_interface()
    vol.SetMute(1 if ativar else 0, None)


def carregar_integracoes():
    if not os.path.exists(INTEGRACOES_PATH):
        padrao = {
            "ias": {
                "zez0": {
                    "tipo": "comando",
                    "comando": "SUBSTITUA_PELO_COMANDO_QUE_INICIA_O_ZEZ0 {tarefa}",
                },
                "celina": {
                    "tipo": "comando",
                    "comando": "SUBSTITUA_PELO_COMANDO_QUE_INICIA_A_CELINA",
                },
                "kroga": {
                    "tipo": "comando",
                    "comando": "SUBSTITUA_PELO_COMANDO_QUE_INICIA_O_KROGA_BOT",
                },
            }
        }
        with open(INTEGRACOES_PATH, "w", encoding="utf-8") as f:
            json.dump(padrao, f, ensure_ascii=False, indent=2)
        return padrao

    with open(INTEGRACOES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def carregar_fluxos():
    if not os.path.exists(FLUXOS_PATH):
        padrao = {
            "fluxos": [
                {
                    "nome": "resumo do dia",
                    "gatilho": "resumo do dia",
                    "etapas": [{"ia": "kroga", "tarefa": "kroga3"}],
                },
                {
                    "nome": "sessão de jogos",
                    "gatilho": "jogar cobrinha",
                    "etapas": [{"ia": "zez0", "tarefa": "snake"}],
                },
            ]
        }
        with open(FLUXOS_PATH, "w", encoding="utf-8") as f:
            json.dump(padrao, f, ensure_ascii=False, indent=2)
        return padrao

    with open(FLUXOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def executar_ia(nome_ia, tarefa, integracoes):
    definicao = integracoes.get("ias", {}).get(nome_ia)
    if not definicao:
        print(f"IA '{nome_ia}' não está cadastrada em integracoes.json.")
        return False

    tipo = definicao.get("tipo")

    if tipo == "comando":
        comando = definicao.get("comando", "")
        if not comando or comando.startswith("SUBSTITUA"):
            print(
                f"O comando de '{nome_ia}' ainda não foi configurado em integracoes.json."
            )
            return False
        comando_final = comando.replace("{tarefa}", tarefa)
        try:
            subprocess.Popen(comando_final, shell=True)
            return True
        except Exception as e:
            print(f"Erro ao acionar {nome_ia}: {e}")
            return False

    if tipo == "webhook":
        url = definicao.get("url", "")
        if not url or url.startswith("SUBSTITUA"):
            print(
                f"A URL de '{nome_ia}' ainda não foi configurada em integracoes.json."
            )
            return False
        try:
            dados = json.dumps({"tarefa": tarefa}).encode("utf-8")
            requisicao = urllib.request.Request(
                url, data=dados, headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(requisicao, timeout=5)
            return True
        except Exception as e:
            print(f"Erro ao acionar {nome_ia} via webhook: {e}")
            return False

    print(f"Tipo de integração desconhecido para '{nome_ia}': {tipo}")
    return False


def executar_fluxo(fluxo, integracoes):
    nome_fluxo = fluxo.get("nome") or fluxo.get("gatilho", "fluxo")
    mostrar_icone("fluxo")
    falar(f"Executando {nome_fluxo}")

    for etapa in fluxo.get("etapas", []):
        nome_ia = etapa.get("ia", "")
        tarefa = etapa.get("tarefa", "")
        if executar_ia(nome_ia, tarefa, integracoes):
            falar(f"{nome_ia} acionado")
        else:
            falar(f"Não consegui acionar {nome_ia}")

    falar(f"{nome_fluxo} concluído")


FRASES_FIXAS = [
    "sair",
    "parar assistente",
    "encerrar assistente",
    "tocar",
    "pausar",
    "próxima música",
    "próxima faixa",
    "música anterior",
    "faixa anterior",
    "aumentar volume",
    "aumenta o volume",
    "diminuir volume",
    "diminui o volume",
    "mudo",
    "silenciar",
    "desmutar",
    "tirar o mudo",
    "mostrar jarvis",
    "abrir jarvis",
    "abrir interface",
    "esconder jarvis",
    "fechar jarvis",
    "fechar interface",
]


def construir_lista_frases(config):
    dinamicas = (
        list(config.get("sites", {}).keys())
        + list(config.get("programas", {}).keys())
        + list(config.get("personalizados", {}).keys())
    )

    frases_ias = []
    for nome_ia in INTEGRACOES.get("ias", {}).keys():
        for verbo in ["iniciar", "abrir", "rodar", "ativar"]:
            frases_ias.append(f"{verbo} {nome_ia}")

    frases_fluxos = [
        fluxo.get("gatilho", "")
        for fluxo in FLUXOS.get("fluxos", [])
        if fluxo.get("gatilho")
    ]

    return FRASES_FIXAS + dinamicas + frases_ias + frases_fluxos


def construir_gramatica(config):
    frases = construir_lista_frases(config)
    return frases + ["pesquisar por", "pesquisa por", "[unk]"]


def corrigir_com_fuzzy(texto, config):
    frases = construir_lista_frases(config)
    mais_proxima = difflib.get_close_matches(texto, frases, n=1, cutoff=0.6)
    return mais_proxima[0] if mais_proxima else texto


def listar_microfones():
    print("\nMicrofones disponíveis:")
    dispositivos = sd.query_devices()
    entradas = []
    for indice, dispositivo in enumerate(dispositivos):
        if dispositivo["max_input_channels"] > 0:
            entradas.append(indice)
            print(f"  [{indice}] {dispositivo['name']}")
    print()
    return entradas


def escolher_microfone(config):
    nome_salvo = config["configuracoes"].get("microfone_nome")
    if nome_salvo:
        for indice, dispositivo in enumerate(sd.query_devices()):
            if (
                dispositivo["max_input_channels"] > 0
                and nome_salvo in dispositivo["name"]
            ):
                return indice
        print(
            f"Microfone salvo ('{nome_salvo}') não foi encontrado agora — tentando pelo índice salvo."
        )

    indice_salvo = config["configuracoes"].get("microfone_indice")
    if indice_salvo is not None:
        return indice_salvo

    if not sys.stdin.isatty():
        print(
            "Execução automática sem terminal interativo — usando o microfone padrão do Windows."
        )
        return None

    entradas = listar_microfones()
    if not entradas:
        print("Nenhum microfone encontrado — usando o dispositivo padrão do Windows.")
        return None

    escolha = input(
        "Digite o número do microfone que você quer usar (Enter para usar o padrão): "
    ).strip()

    if not escolha:
        return None

    try:
        indice = int(escolha)
    except ValueError:
        print("Número inválido, usando o dispositivo padrão.")
        return None

    config["configuracoes"]["microfone_indice"] = indice
    config["configuracoes"]["microfone_nome"] = sd.query_devices()[indice]["name"]
    salvar_config(config)
    print(
        f"Microfone [{indice}] salvo em comandos.json. Da próxima vez não vai perguntar de novo."
    )
    return indice


def aplicar_ganho(dados_bytes, ganho):
    amostras = np.frombuffer(dados_bytes, dtype=np.int16).astype(np.float32)
    amostras *= ganho
    amostras = np.clip(amostras, -32768, 32767).astype(np.int16)
    return amostras.tobytes()


def abrir_programa(caminho):
    try:
        subprocess.Popen(caminho, shell=True)
        return True
    except Exception as e:
        print(f"Erro ao abrir programa: {e}")
        return False


def executar_comando_personalizado(comando_shell):
    try:
        subprocess.Popen(comando_shell, shell=True)
        return True
    except Exception as e:
        print(f"Erro ao executar comando: {e}")
        return False


def processar_comando(texto, config):
    texto = texto.lower().strip()
    if not texto:
        return True

    if not texto.startswith("pesquisar por") and not texto.startswith("pesquisa por"):
        corrigido = corrigir_com_fuzzy(texto, config)
        if corrigido != texto:
            print(f"(entendi como: {corrigido})")
            texto = corrigido

    if any(p in texto for p in ["sair", "parar assistente", "encerrar assistente"]):
        falar("Encerrando assistente. Até logo!")
        return False

    for fluxo in FLUXOS.get("fluxos", []):
        gatilho = fluxo.get("gatilho", "")
        if gatilho and gatilho in texto:
            executar_fluxo(fluxo, INTEGRACOES)
            return True

    if "tocar" in texto or "pausar" in texto:
        keyboard.send("play/pause media")
        mostrar_icone("midia")
        falar("Ok")
        return True
    if "próxima música" in texto or "próxima faixa" in texto:
        keyboard.send("next track")
        mostrar_icone("midia")
        falar("Próxima faixa")
        return True
    if "música anterior" in texto or "faixa anterior" in texto:
        keyboard.send("previous track")
        mostrar_icone("midia")
        falar("Faixa anterior")
        return True

    if "aumentar volume" in texto or "aumenta o volume" in texto:
        ajustar_volume(0.15)
        mostrar_icone("volume")
        falar("Volume aumentado")
        return True
    if "diminuir volume" in texto or "diminui o volume" in texto:
        ajustar_volume(-0.15)
        mostrar_icone("volume")
        falar("Volume diminuído")
        return True
    if "mudo" in texto or "silenciar" in texto:
        mudo(True)
        mostrar_icone("volume")
        falar("Áudio mudo")
        return True
    if "desmutar" in texto or "tirar o mudo" in texto:
        mudo(False)
        mostrar_icone("volume")
        falar("Áudio ativado")
        return True

    if (
        "mostrar jarvis" in texto
        or "abrir jarvis" in texto
        or "abrir interface" in texto
    ):
        if JANELA is not None:
            JANELA.show()
            falar("Interface ativada")
        return True
    if (
        "esconder jarvis" in texto
        or "fechar jarvis" in texto
        or "fechar interface" in texto
    ):
        if JANELA is not None:
            JANELA.hide()
            falar("Interface ocultada")
        return True

    for nome_ia in INTEGRACOES.get("ias", {}).keys():
        if nome_ia in texto and any(
            v in texto for v in ["iniciar", "abrir", "rodar", "ativar"]
        ):
            mostrar_icone("ia")
            if executar_ia(nome_ia, "abrir", INTEGRACOES):
                falar(f"Acionando {nome_ia}")
            else:
                falar(f"Não consegui acionar {nome_ia}")
            return True

    if texto.startswith("pesquisar por") or texto.startswith("pesquisa por"):
        termo = texto.split("por", 1)[1].strip()
        webbrowser.open(f"https://www.google.com/search?q={termo}")
        mostrar_icone("site")
        falar(f"Pesquisando por {termo}")
        return True

    for nome, url in config.get("sites", {}).items():
        if nome in texto:
            webbrowser.open(url)
            mostrar_icone("site")
            falar(f"Abrindo {nome}")
            return True

    for nome, caminho in config.get("programas", {}).items():
        if nome in texto:
            mostrar_icone("programa")
            if abrir_programa(caminho):
                falar(f"Abrindo {nome}")
            else:
                falar(f"Não consegui abrir {nome}")
            return True

    for nome, cmd in config.get("personalizados", {}).items():
        if nome in texto:
            mostrar_icone("programa")
            if executar_comando_personalizado(cmd):
                falar(f"Executando {nome}")
            else:
                falar(f"Não consegui executar {nome}")
            return True

    falar("Não entendi esse comando")
    return True


fila_audio = queue.Queue()
fila_comandos = queue.Queue()
GANHO_ATUAL = 6.0


def callback_audio(indata, frames, time_info, status):
    if status:
        print(status)
    dados = aplicar_ganho(bytes(indata), GANHO_ATUAL)
    fila_audio.put(dados)


def verificar_modelo():
    if not os.path.isdir(MODELO_PATH) or not os.listdir(MODELO_PATH):
        raise FileNotFoundError(
            "Modelo do Vosk não encontrado em 'modelo_vosk/'.\n"
            "Baixe o modelo em português e extraia nessa pasta — "
            "instruções completas no README.md."
        )


def abrir_entrada_audio(
    indice_microfone, callback, tentativas_max=20, intervalo_segundos=3
):
    for tentativa in range(1, tentativas_max + 1):
        try:
            return sd.RawInputStream(
                samplerate=TAXA_AMOSTRAGEM,
                blocksize=8000,
                dtype="int16",
                channels=1,
                device=indice_microfone,
                callback=callback,
            )
        except Exception as e:
            print(
                f"Sistema de áudio ainda não está pronto ({e}). Tentativa {tentativa}/{tentativas_max}..."
            )
            time.sleep(intervalo_segundos)
    raise RuntimeError(
        "Não foi possível acessar o microfone depois de várias tentativas."
    )


def thread_reconhecimento_voz(
    indice_microfone, reconhecedor, tempo_silencio_max=1.6, tempo_max_frase=12
):
    LIMIAR_SILENCIO = 350
    TAMANHO_CHUNK_SEGUNDOS = 8000 / TAXA_AMOSTRAGEM

    segundos_silencio = 0.0
    segundos_falando = 0.0
    teve_fala = False

    with abrir_entrada_audio(indice_microfone, callback_audio):
        print("Ouvindo... (fale um comando ou diga 'sair')")
        while True:
            dados = fila_audio.get()
            reconhecedor.AcceptWaveform(dados)

            amostras = np.frombuffer(dados, dtype=np.int16).astype(np.float32)
            volume = np.sqrt(np.mean(amostras**2)) if len(amostras) else 0.0

            if volume > LIMIAR_SILENCIO:
                teve_fala = True
                segundos_silencio = 0.0
                segundos_falando += TAMANHO_CHUNK_SEGUNDOS
            else:
                segundos_silencio += TAMANHO_CHUNK_SEGUNDOS

            frase_completa = teve_fala and segundos_silencio >= tempo_silencio_max
            frase_longa_demais = teve_fala and segundos_falando >= tempo_max_frase

            if frase_completa or frase_longa_demais:
                resultado = json.loads(reconhecedor.FinalResult())
                texto = resultado.get("text", "")
                if texto:
                    print(f"[voz] {texto}")
                    fila_comandos.put(texto)
                reconhecedor.Reset()
                teve_fala = False
                segundos_silencio = 0.0
                segundos_falando = 0.0


def thread_entrada_texto():
    if not sys.stdin.isatty():
        return
    print("Também dá pra digitar um comando aqui e apertar Enter.")
    while True:
        try:
            linha = input()
        except (EOFError, OSError):
            break
        linha = linha.strip()
        if linha:
            fila_comandos.put(linha)


def loop_reconhecimento(janela):
    global JANELA, GANHO_ATUAL, INTEGRACOES, FLUXOS
    JANELA = janela

    try:
        verificar_modelo()
        config = carregar_config()
        INTEGRACOES = carregar_integracoes()
        FLUXOS = carregar_fluxos()

        GANHO_ATUAL = config["configuracoes"].get("ganho_audio", 6.0)
        indice_microfone = escolher_microfone(config)

        print(
            "Carregando modelo de reconhecimento de voz (pode levar alguns segundos)..."
        )
        modelo = Model(MODELO_PATH)
        gramatica = construir_gramatica(config)
        reconhecedor = KaldiRecognizer(
            modelo, TAXA_AMOSTRAGEM, json.dumps(gramatica, ensure_ascii=False)
        )

        threading.Thread(
            target=thread_reconhecimento_voz,
            args=(
                indice_microfone,
                reconhecedor,
                config["configuracoes"].get("tempo_silencio_max", 1.6),
                config["configuracoes"].get("tempo_max_frase", 12),
            ),
            daemon=True,
        ).start()
        threading.Thread(target=thread_entrada_texto, daemon=True).start()

        falar(
            f"{saudacao_por_horario()}, senhor. Assistente ativado, pode falar ou digitar seus comandos."
        )

        continuar = True
        while continuar:
            texto = fila_comandos.get()
            continuar = processar_comando(texto, config)
    except FileNotFoundError as e:
        print(str(e))
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
    finally:
        janela.destroy()


def main():
    janela = webview.create_window(
        "Jarvis",
        INTERFACE_PATH,
        width=260,
        height=260,
        frameless=True,
        easy_drag=True,
        on_top=True,
        transparent=True,
        hidden=True,
    )
    webview.start(loop_reconhecimento, janela)


if __name__ == "__main__":
    main()
