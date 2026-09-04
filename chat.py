import json
import os
import queue
import subprocess
import webbrowser
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
    """Carrega comandos.json, criando um padrão se não existir."""
    if not os.path.exists(CONFIG_PATH):
        padrao = {
            "programas": {
                "bloco de notas": "notepad.exe",
                "calculadora": "calc.exe",
                "navegador": "chrome.exe",
                "explorador de arquivos": "explorer.exe",
                "paint": "mspaint.exe"
            },
            "sites": {
                "youtube": "https://youtube.com",
                "google": "https://google.com",
                "gmail": "https://mail.google.com"
            },
            "personalizados": {
                "abrir downloads": f'explorer.exe {os.path.join(os.path.expanduser("~"), "Downloads")}'
            }
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(padrao, f, ensure_ascii=False, indent=2)
        return padrao

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


motor_voz = pyttsx3.init()
motor_voz.setProperty("rate", 175)

for voz in motor_voz.getProperty("voices"):
    if "brazil" in voz.name.lower() or "portuguese" in voz.name.lower() or "pt" in voz.id.lower():
        motor_voz.setProperty("voice", voz.id)
        break


def falar(texto):
    print(f"[Assistente] {texto}")
    motor_voz.say(texto)
    motor_voz.runAndWait()

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


def callback_audio(indata, frames, time_info, status):
    if status:
        print(status)
    fila_audio.put(bytes(indata))


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

    print("Carregando modelo de reconhecimento de voz (pode levar alguns segundos)...")
    modelo = Model(MODELO_PATH)
    reconhecedor = KaldiRecognizer(modelo, TAXA_AMOSTRAGEM)

    falar("Assistente de voz offline ativado. Pode falar seus comandos.")

    continuar = True
    with sd.RawInputStream(
        samplerate=TAXA_AMOSTRAGEM,
        blocksize=8000,
        dtype="int16",
        channels=1,
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
