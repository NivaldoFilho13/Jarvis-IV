import difflib
import json
import os
import queue
import subprocess
import webbrowser
from datetime import datetime

import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer

import pyttsx3
import keyboard

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

PASTA_BASE = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(PASTA_BASE, "comandos.json")
MODELO_PATH = os.path.join(PASTA_BASE, "modelo_vosk")

TAXA_AMOSTRAGEM = 16000


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
            "configuracoes": {"microfone_indice": None, "ganho_audio": 6.0},
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(padrao, f, ensure_ascii=False, indent=2)
        return padrao

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    config.setdefault("configuracoes", {})
    config["configuracoes"].setdefault("microfone_indice", None)
    config["configuracoes"].setdefault("ganho_audio", 6.0)
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
    motor_voz.say(texto)
    motor_voz.runAndWait()


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
]


def construir_lista_frases(config):
    dinamicas = (
        list(config.get("sites", {}).keys())
        + list(config.get("programas", {}).keys())
        + list(config.get("personalizados", {}).keys())
    )
    return FRASES_FIXAS + dinamicas


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

    indice_salvo = config["configuracoes"].get("microfone_indice")
    if indice_salvo is not None:
        return indice_salvo

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

    if "tocar" in texto or "pausar" in texto:
        keyboard.send("play/pause media")
        falar("Ok")
        return True
    if "próxima música" in texto or "próxima faixa" in texto:
        keyboard.send("next track")
        falar("Próxima faixa")
        return True
    if "música anterior" in texto or "faixa anterior" in texto:
        keyboard.send("previous track")
        falar("Faixa anterior")
        return True

    if "aumentar volume" in texto or "aumenta o volume" in texto:
        ajustar_volume(0.15)
        falar("Volume aumentado")
        return True
    if "diminuir volume" in texto or "diminui o volume" in texto:
        ajustar_volume(-0.15)
        falar("Volume diminuído")
        return True
    if "mudo" in texto or "silenciar" in texto:
        mudo(True)
        falar("Áudio mudo")
        return True
    if "desmutar" in texto or "tirar o mudo" in texto:
        mudo(False)
        falar("Áudio ativado")
        return True

    if texto.startswith("pesquisar por") or texto.startswith("pesquisa por"):
        termo = texto.split("por", 1)[1].strip()
        webbrowser.open(f"https://www.google.com/search?q={termo}")
        falar(f"Pesquisando por {termo}")
        return True

    for nome, url in config.get("sites", {}).items():
        if nome in texto:
            webbrowser.open(url)
            falar(f"Abrindo {nome}")
            return True

    for nome, caminho in config.get("programas", {}).items():
        if nome in texto:
            if abrir_programa(caminho):
                falar(f"Abrindo {nome}")
            else:
                falar(f"Não consegui abrir {nome}")
            return True

    for nome, cmd in config.get("personalizados", {}).items():
        if nome in texto:
            if executar_comando_personalizado(cmd):
                falar(f"Executando {nome}")
            else:
                falar(f"Não consegui executar {nome}")
            return True

    falar("Não entendi esse comando")
    return True


fila_audio = queue.Queue()
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


def main():
    verificar_modelo()
    config = carregar_config()

    global GANHO_ATUAL
    GANHO_ATUAL = config["configuracoes"].get("ganho_audio", 6.0)
    indice_microfone = escolher_microfone(config)

    print("Carregando modelo de reconhecimento de voz (pode levar alguns segundos)...")
    modelo = Model(MODELO_PATH)
    gramatica = construir_gramatica(config)
    reconhecedor = KaldiRecognizer(
        modelo, TAXA_AMOSTRAGEM, json.dumps(gramatica, ensure_ascii=False)
    )

    falar(
        f"{saudacao_por_horario()}, senhor. Assistente ativado, pode falar seus comandos."
    )

    continuar = True
    with sd.RawInputStream(
        samplerate=TAXA_AMOSTRAGEM,
        blocksize=8000,
        dtype="int16",
        channels=1,
        device=indice_microfone,
        callback=callback_audio,
    ):
        print("Ouvindo... (fale um comando ou diga 'sair')")
        while continuar:
            dados = fila_audio.get()
            if reconhecedor.AcceptWaveform(dados):
                resultado = json.loads(reconhecedor.Result())
                texto = resultado.get("text", "")
                if texto:
                    print(f"Você disse: {texto}")
                    continuar = processar_comando(texto, config)


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(str(e))
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
