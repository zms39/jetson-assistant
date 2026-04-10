import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

MIC_INDEX = 0        # change to your mic index from Phase 2
RECORD_SECONDS = 5   # how long to listen after wake word

class SpeechToText:
    def __init__(self):
        print("Loading Whisper model... (first time takes ~30 seconds)")
        self.model = WhisperModel("small", device="cpu", compute_type="int8")
        print("Whisper ready.")

    def listen_and_transcribe(self):
        print("Listening...")
        audio = sd.rec(
            int(RECORD_SECONDS * 16000),
            samplerate=16000,
            channels=1,
            dtype='float32',
            device=MIC_INDEX
        )
        sd.wait()
        audio_flat = audio.flatten()
        segments, _ = self.model.transcribe(audio_flat, beam_size=1)
        text = " ".join([s.text.strip() for s in segments])
        print(f"You said: {text}")
        return text
