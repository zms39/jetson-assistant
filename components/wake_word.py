import queue
from typing import Optional

import numpy as np
import openwakeword
import sounddevice as sd
from openwakeword.model import Model

MIC_INDEX = 24
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1280  # 80 ms at 16 kHz
DEFAULT_THRESHOLD = 0.5
DEFAULT_VAD_THRESHOLD = 0.3


class WakeWordListener:
    def __init__(
        self,
        mic_index: int = MIC_INDEX,
        threshold: float = DEFAULT_THRESHOLD,
        vad_threshold: float = DEFAULT_VAD_THRESHOLD,
        enable_speex_noise_suppression: bool = False,
        wakeword_models: Optional[list[str]] = None,
    ):
        self.mic_index = mic_index
        self.threshold = threshold
        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue()

        # Download included pre-trained models once, then instantiate the detector.
        # Leaving wakeword_models empty loads the bundled pre-trained models.
        openwakeword.utils.download_models()
        self.model = Model(
            wakeword_models=wakeword_models or [],
            vad_threshold=vad_threshold,
            enable_speex_noise_suppression=enable_speex_noise_suppression,
        )

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}")

        pcm = np.frombuffer(indata, dtype=np.int16).copy()
        self.audio_queue.put(pcm)

    def wait_for_wake_word(self) -> str:
        print("Waiting for wake word...")

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=CHUNK_SIZE,
            device=self.mic_index,
            channels=CHANNELS,
            dtype="int16",
            callback=self._audio_callback,
        ):
            while True:
                audio_chunk = self.audio_queue.get()
                prediction = self.model.predict(audio_chunk)

                for wake_name, score in prediction.items():
                    if score >= self.threshold:
                        print(f"Wake word detected: {wake_name} ({score:.3f})")
                        self.model.reset()
                        return wake_name
