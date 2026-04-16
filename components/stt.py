import sounddevice as sd
import numpy as np
from scipy.signal import resample_poly
from faster_whisper import WhisperModel

MIC_INDEX = 24
RECORD_SECONDS = 5
NATIVE_RATE = 48000
TARGET_RATE = 16000

class SpeechToText:
    def __init__(self):
        print("Loading Whisper model... (first time takes ~30 seconds)")
        self.model = WhisperModel("small", device="cpu", compute_type="int8")
        print("Whisper ready.")

    def listen_and_transcribe(self):
        print("Listening...")
        audio = sd.rec(
            int(RECORD_SECONDS * NATIVE_RATE),
            samplerate=NATIVE_RATE,
            channels=1,
            dtype='float32',
            device=MIC_INDEX
        )
        sd.wait()
        audio_flat = audio.flatten()

        # Downsample to 16kHz for Whisper
        audio_16k = resample_poly(audio_flat, TARGET_RATE, NATIVE_RATE)

        segments, _ = self.model.transcribe(audio_16k, beam_size=1)
        text = " ".join([s.text.strip() for s in segments])
        print(f"You said: {text}")
        return text