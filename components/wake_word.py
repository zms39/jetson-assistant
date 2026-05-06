import queue
import time

import numpy as np
import openwakeword
import sounddevice as sd
from openwakeword.model import Model
from scipy.signal import resample_poly

MIC_INDEX = 0
INPUT_RATE = 48000
MODEL_RATE = 16000
CHANNELS = 1
INPUT_CHUNK_SIZE = 7680  # 80 ms at 48 kHz


class WakeWordListener:
    def __init__(
        self,
        mic_index: int = MIC_INDEX,
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

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")
        pcm = np.frombuffer(indata, dtype=np.int16).copy()
        self.audio_queue.put(pcm)

    def _flush_model_state(self):
        # openWakeWord can keep prior audio context around after a hit.
        # Feed silence until predictions drop below threshold.
        flush_chunk = np.zeros(1280, dtype=np.int16)   # 80 ms at 16 kHz
        max_flush_iters = 25  # about 2 seconds / 32k+ samples total

        for _ in range(max_flush_iters):
            prediction = self.model.predict(flush_chunk)
            still_hot = any(score >= self.threshold for score in prediction.values())
            if not still_hot:
                break

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

                audio_float = audio_chunk.astype(np.float32)
                audio_16k = resample_poly(audio_float, MODEL_RATE, INPUT_RATE)
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

                        self._flush_model_state()
                        time.sleep(self.cooldown_seconds)
                        return wake_name