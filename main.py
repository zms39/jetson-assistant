import sys
import time
import threading
import requests

sys.path.insert(0, '/home/cwru26ai/assistant')

from components.stt import SpeechToText
from components.llm import LLMClient
from components.tts import TextToSpeech
from components.wake_word import WakeWordListener
from display.display_manager import DisplayManager

MIC_INDEX = 0
WAKE_THRESHOLD = 0.7
VAD_THRESHOLD = 0.3


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

    wake = WakeWordListener(mic_index=MIC_INDEX, threshold=WAKE_THRESHOLD, vad_threshold=VAD_THRESHOLD)
    stt  = SpeechToText(mic_index=MIC_INDEX)
    llm  = LLMClient()
    tts  = TextToSpeech()
    display = DisplayManager()

    phase           = "idle"   # idle | listening | thinking | speaking
    working         = False    # True while background thread is running
    result          = [None]   # thread writes return value here
    response_text   = ""
    transcribed     = ""

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

    # Kick off wake-word detection straight away so we don't sit idle.
    launch(wake.wait_for_wake_word)

    while True:
        # Display always updates — this is what keeps the waveform alive.
        display.set_state(phase, response_text)
        display.update()

        # While a thread is running, just keep refreshing the display.
        if working:
            continue

        # --- Thread finished: advance the state machine ---

        if phase == "idle":
            # Wake word detected — start listening.
            phase = "listening"
            launch(stt.listen_and_transcribe)

        elif phase == "listening":
            transcribed = result[0] or ""
            if transcribed.strip():
                phase = "thinking"
                launch(llm.query, transcribed)
            else:
                # Nothing heard — go back to waiting.
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