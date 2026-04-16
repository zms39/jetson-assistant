import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from faster_whisper import WhisperModel

MIC_INDEX = 24
RECORD_SECONDS = 5
NATIVE_RATE = 48000
TARGET_RATE = 16000


class SpeechToText:
    def __init__(self, mic_index: int = MIC_INDEX, record_seconds: int = RECORD_SECONDS):
        self.mic_index = mic_index
        self.record_seconds = record_seconds

        print("Loading Whisper model... (first time takes ~30 seconds)")
        self.model = WhisperModel("small", device="cpu", compute_type="int8")
        print("Whisper ready.")

    def listen_and_transcribe(self) -> str:
        print("Listening for command...")
        audio = sd.rec(
            int(self.record_seconds * NATIVE_RATE),
            samplerate=NATIVE_RATE,
            channels=1,
            dtype="float32",
            device=self.mic_index,
        )
        sd.wait()

        audio_flat = np.squeeze(audio)

        # Downsample to 16 kHz for Whisper.
        audio_16k = resample_poly(audio_flat, TARGET_RATE, NATIVE_RATE)

        segments, _ = self.model.transcribe(audio_16k, beam_size=1)
        text = " ".join(segment.text.strip() for segment in segments).strip()

        print(f"You said: {text}")
        return text
