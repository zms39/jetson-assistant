import queue
import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
import openwakeword
from openwakeword.model import Model
import time

MIC_INDEX = 24

# Mic capture rate
INPUT_RATE = 48000

# openWakeWord expects 16 kHz int16 PCM
MODEL_RATE = 16000

CHANNELS = 1

# 80 ms chunk at 48 kHz = 3840 samples
INPUT_CHUNK_SIZE = 3840

class WakeWordListener:
    def __init__(
        self,
        mic_index: int = 24,
        threshold: float = 0.5,
        vad_threshold: float = 0.3,
        wakeword_models=None,
        cooldown_seconds: float = 1.5,
    ):
        self.mic_index = mic_index
        self.threshold = threshold
        self.cooldown_seconds = cooldown_seconds
        self.audio_queue = queue.Queue()

        openwakeword.utils.download_models()

        self.model = Model(
            wakeword_models=wakeword_models if wakeword_models is not None else [],
            vad_threshold=vad_threshold,
        )

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")

        pcm = np.frombuffer(indata, dtype=np.int16).copy()
        self.audio_queue.put(pcm)

    def wait_for_wake_word(self):
        print("Waiting for wake word...")

        with sd.RawInputStream(
            samplerate=INPUT_RATE,
            blocksize=INPUT_CHUNK_SIZE,
            device=self.mic_index,
            channels=CHANNELS,
            dtype="int16",
            callback=self._audio_callback,
        ):
            while True:
                audio_chunk = self.audio_queue.get()

                # convert int16 -> float for resampling
                audio_float = audio_chunk.astype(np.float32)

                # 48k -> 16k
                audio_16k = resample_poly(audio_float, MODEL_RATE, INPUT_RATE)

                # back to int16 PCM
                audio_16k = np.clip(audio_16k, -32768, 32767).astype(np.int16)

                prediction = self.model.predict(audio_16k)

                for wake_name, score in prediction.items():
                    if score >= self.threshold:
                        print(f"Wake word detected: {wake_name} ({score:.3f})")

                        while not self.audio_queue.empty():
                            try:
                                self.audio_queue.get_nowait()
                            except Exception:
                                break

                        time.sleep(self.cooldown_seconds)
                        return wake_name