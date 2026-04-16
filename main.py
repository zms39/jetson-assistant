import sys
import time

import requests

sys.path.insert(0, "/home/cwru26ai/assistant")

from components.stt import SpeechToText
from components.llm import LLMClient
from components.tts import TextToSpeech
from components.wake_word import WakeWordListener
from display.display_manager import DisplayManager

MIC_INDEX = 24
WAKE_THRESHOLD = 0.7
VAD_THRESHOLD = 0.3
POST_RESPONSE_COOLDOWN = 1.5


def wait_for_ollama():
    print("Waiting for Ollama...")
    while True:
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                print("Ollama ready.")
                return
        except Exception:
            pass
        time.sleep(2)


def main():
    wait_for_ollama()

    wake = WakeWordListener(
        mic_index=MIC_INDEX,
        threshold=WAKE_THRESHOLD,
        vad_threshold=VAD_THRESHOLD,
    )
    stt = SpeechToText(mic_index=MIC_INDEX)
    llm = LLMClient()
    tts = TextToSpeech()
    display = DisplayManager()

    state = "idle"
    response_text = ""
    transcribed_text = ""

    print("Assistant running. Say the wake word to trigger listening.")

    while True:
        display.set_state(state, response_text)
        display.update()

        if state == "idle":
            wake_name = wake.wait_for_wake_word()
            print(f"Activated by: {wake_name}")
            state = "listening"

        elif state == "listening":
            transcribed_text = stt.listen_and_transcribe()

            if transcribed_text.strip():
                print(f"User said: {transcribed_text}")
                state = "thinking"
            else:
                print("No speech detected. Returning to idle.")
                state = "idle"

        elif state == "thinking":
            print("Querying LLM...")
            response_text = llm.query(transcribed_text)
            print(f"Assistant: {response_text}")
            state = "speaking"

        elif state == "speaking":
            tts.speak(response_text)

            response_text = ""
            transcribed_text = ""

            time.sleep(POST_RESPONSE_COOLDOWN)
            state = "idle"


if __name__ == "__main__":
    main()