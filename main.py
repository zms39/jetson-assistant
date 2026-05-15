import sys
import time
import threading
import requests
import sounddevice as sd

# Allow imports from the project root regardless of working directory
sys.path.insert(0, '/home/cwru26ai/assistant')

from components.stt import SpeechToText
from components.llm import LLMClient
from components.tts import TextToSpeech
from components.wake_word import WakeWordListener
from display.display_manager import DisplayManager, ART_KEYWORDS, NEXT_KEYWORDS

# Wake word confidence threshold (0.0 - 1.0)
# Lower values increase sensitivity but risk false positives
WAKE_THRESHOLD = 0.7

# Voice activity detection threshold for openWakeWord's built-in VAD
VAD_THRESHOLD = 0.3

# Initialization of the Ollama model
def wait_for_ollama():
    """
    Polls the local Ollama REST API until it is ready.
    Ollama can take several seconds to initialize after the Docker
    container starts, so main.py blocks here before loading other components.
    """
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

# Finds microphone index
def _find_mic_index():
    for i, dev in enumerate(sd.query_devices()):
        if 'usb' in dev['name'].lower() and dev['max_input_channels'] > 0:
            return i
    raise RuntimeError("USB microphone not found")

def main():
    wait_for_ollama()

    # Initialise all components
    wake = WakeWordListener(mic_index = _find_mic_index(), threshold = WAKE_THRESHOLD, vad_threshold = VAD_THRESHOLD)
    stt = SpeechToText(mic_index = _find_mic_index())
    llm = LLMClient()
    tts = TextToSpeech()
    display = DisplayManager()

    # State machine phases: idle -> listening -> thinking -> speaking -> idle
    phase = "idle"
    working = False # True while a background thread is running
    result = [None] # Shared result slot written by background threads
    response_text = ""
    transcribed_STT_output = ""

    def launch(fn, *args):
        """
        Runs fn(*args) in a daemon thread so the pygame display loop
        (which runs on the main thread) never blocks.
        The result is stored in result[0] and working is cleared on completion.
        """
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

    # Kick off wake word detection immediately on startup
    launch(wake.wait_for_wake_word)

    while True:
        # Push the current phase and any response text to the display each frame
        display.set_state(phase, response_text)
        display.update()

        # While a background thread is active, spin and keep the display alive
        if working:
            time.sleep(0.01)
            continue

        if phase == "idle":
            # Wake word was detected (background thread finished); start listening
            phase = "listening"
            launch(stt.listen_and_transcribe)

        elif phase == "listening":
            transcribed_STT_output = result[0] or ""
            lower = transcribed_STT_output.lower()

            if any(kw in lower for kw in NEXT_KEYWORDS):
                # User asked to cycle the dot matrix animation
                display.next_art_mode()
                print(f"Art mode -> {display._dot_art.MODES[display._dot_art.mode_idx]}")
                phase = "idle"
                launch(wake.wait_for_wake_word)

            elif any(kw in lower for kw in ART_KEYWORDS):
                # User toggled the dot matrix screensaver on or off
                display.toggle_art_mode()
                print(f"Art mode {'on' if display.art_mode else 'off'}")
                phase = "idle"
                launch(wake.wait_for_wake_word)

            elif transcribed_STT_output.strip():
                # Valid command received, send to the LLM
                phase = "thinking"
                launch(llm.query, transcribed_STT_output)

            else:
                # Nothing heard, go back to waiting for the wake word
                phase = "idle"
                launch(wake.wait_for_wake_word)

        elif phase == "thinking":
            # LLM has returned a response, speak it aloud
            response_text = result[0] or ""
            phase = "speaking"
            launch(tts.speak, response_text)

        elif phase == "speaking":
            # TTS finished, reset and return to idle wake word detection
            response_text = ""
            transcribed_STT_output = ""
            phase = "idle"
            launch(wake.wait_for_wake_word)


if __name__ == "__main__":
    main()