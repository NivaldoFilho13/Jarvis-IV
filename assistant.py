import os
import sys
import time

import speech_recognition as sr
import pyttsx3
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("ERRO: defina ANTHROPIC_API_KEY no arquivo .env (veja .env.example).")
    sys.exit(1)

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
WAKE_WORD = os.getenv("WAKE_WORD", "claude").lower()
IDIOMA_RECONHECIMENTO = os.getenv("SPEECH_LANGUAGE", "pt-BR")

client = Anthropic(api_key=API_KEY)

conversation_history: list[dict] = []
MAX_HISTORY_MESSAGES = 10  

def criar_engine_tts() -> pyttsx3.Engine:
    engine = pyttsx3.init()
    engine.setProperty("rate", 175)

    for voice in engine.getProperty("voices"):
        nome = (voice.name or "").lower()
        idioma = "".join(voice.languages) if voice.languages else ""
        if "portuguese" in nome or "brazil" in nome or "pt" in str(idioma).lower():
            engine.setProperty("voice", voice.id)
            break

    return engine


tts_engine = criar_engine_tts()


def falar(texto: str) -> None:
    print(f"[Claude] {texto}")
    tts_engine.say(texto)
    tts_engine.runAndWait()

def perguntar_claude(pergunta: str) -> str:
    conversation_history.append({"role": "user", "content": pergunta})

    historico_recente = conversation_history[-MAX_HISTORY_MESSAGES:]

    try:
        resposta = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=(
                "Você é um assistente de voz. Responda de forma direta, "
                "natural e curta (poucas frases), pois a resposta será "
                "falada em voz alta, não lida."
            ),
            messages=historico_recente,
        )
        texto_resposta = "".join(
            bloco.text for bloco in resposta.content if bloco.type == "text"
        )
    except Exception as e:
        texto_resposta = f"Tive um problema para falar com a API: {e}"

    conversation_history.append({"role": "assistant", "content": texto_resposta})
    return texto_resposta

def escutar_frase(recognizer: sr.Recognizer, mic: sr.Microphone, timeout: float | None = None) -> str | None:
    try:
        with mic as source:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=8)
        texto = recognizer.recognize_google(audio, language=IDIOMA_RECONHECIMENTO)
        return texto
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"Erro no serviço de reconhecimento de voz: {e}")
        return None


def extrair_comando(texto: str, wake_word: str) -> str | None:

    texto_lower = texto.lower()
    if wake_word not in texto_lower:
        return None

    idx = texto_lower.find(wake_word)
    resto = texto[idx + len(wake_word):].strip(" ,.:;!?")
    return resto


def main() -> None:
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True

    try:
        mic = sr.Microphone()
    except OSError as e:
        print(f"Não foi possível acessar o microfone: {e}")
        sys.exit(1)

    print("Calibrando microfone para o ruído ambiente...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.5)

    print(f'Pronto. Diga "{WAKE_WORD}" seguido do seu pedido (ex: "{WAKE_WORD}, me fale sobre o clima").')
    print("Pressione Ctrl+C para encerrar.\n")

    while True:
        try:
            texto = escutar_frase(recognizer, mic, timeout=None)
            if not texto:
                continue

            print(f"[Você disse] {texto}")
            comando = extrair_comando(texto, WAKE_WORD)

            if comando is None:
                continue

            if comando == "":
                falar("Pode falar, estou ouvindo.")
                texto_seguinte = escutar_frase(recognizer, mic, timeout=6)
                if not texto_seguinte:
                    falar("Não entendi, pode repetir depois dizendo Claude de novo.")
                    continue
                comando = texto_seguinte

            print(f"[Comando detectado] {comando}")
            resposta = perguntar_claude(comando)
            falar(resposta)

        except KeyboardInterrupt:
            print("\nEncerrando o assistente.")
            break
        except Exception as e:
            print(f"Erro inesperado: {e}")
            time.sleep(1)
             
if __name__ == "__main__":
    main()
