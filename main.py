import sys
import time
import threading
import requests

sys.path.insert(0, '/home/cwru26ai/assistant')

from components.stt import SpeechToText
from components.llm import LLMClient
from components.tts import TextToSpeech
from components.wake_word import WakeWordListener
from display.display_manager import DisplayManager, ART_KEYWORDS, NEXT_KEYWORDS

# The variables that indicate the volume control for environment
MIC_INDEX = 0
WAKE_THRESHOLD = 0.7
VAD_THRESHOLD = 0.3

# Initialization of the Ollama model
def wait_for_ollama():
    print("Waiting for Ollama...")
    while True:
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.status_code == 200:
                print("Ollama ready.")
                return
        except Exception:
            pass
        time.sleep(2)


def main():
    wait_for_ollama()

    # Listen for the wake word
    wake = WakeWordListener(mic_index=MIC_INDEX, threshold=WAKE_THRESHOLD, vad_threshold=VAD_THRESHOLD)
    stt = SpeechToText(mic_index=MIC_INDEX)
    llm = LLMClient()
    tts = TextToSpeech()
    display = DisplayManager()

    # Details the variables for each phase
    phase = "idle"
    working = False
    result = [None]
    response_text = ""
    transcribed = ""

    # Initial code to check for errors in the loading of the models
    def launch(fn, *args):
        nonlocal working
        working = True
        result[0] = None
        def _run():
            nonlocal working
            try:
                result[0] = fn(*args)
            except Exception as e:
                print(f"[thread error] {fn.__name__}: {e}")
                result[0] = None
            working = False
        threading.Thread(target=_run, daemon=True).start()

    launch(wake.wait_for_wake_word)

    while True:
        # Display settings
        display.set_state(phase, response_text)
        display.update()

        if working:
            time.sleep(0.01)
            continue

        if phase == "idle":
            phase = "listening"
            launch(stt.listen_and_transcribe)

        elif phase == "listening":
            transcribed = result[0] or ""
            lower = transcribed.lower()

            if any(kw in lower for kw in NEXT_KEYWORDS):
                display.next_art_mode()
                print(f"Art mode -> {display._dot_art.MODES[display._dot_art.mode_idx]}")
                phase = "idle"
                launch(wake.wait_for_wake_word)

            elif any(kw in lower for kw in ART_KEYWORDS):
                display.toggle_art_mode()
                print(f"Art mode {'on' if display.art_mode else 'off'}")
                phase = "idle"
                launch(wake.wait_for_wake_word)

            elif transcribed.strip():
                phase = "thinking"
                launch(llm.query, transcribed)

            else:
                phase = "idle"
                launch(wake.wait_for_wake_word)

        elif phase == "thinking":
            response_text = result[0] or ""
            phase = "speaking"
            launch(tts.speak, response_text)

        elif phase == "speaking":
            response_text = ""
            transcribed   = ""
            phase = "idle"
            launch(wake.wait_for_wake_word)


if __name__ == "__main__":
    main()