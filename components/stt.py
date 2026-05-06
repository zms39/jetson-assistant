import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from faster_whisper import WhisperModel

MIC_INDEX = 0
NATIVE_RATE = 48000
TARGET_RATE = 16000

MAX_RECORD_SECONDS = 5
CHUNK_SECONDS = 0.25
SILENCE_SECONDS_TO_STOP = 1.0
SILENCE_THRESHOLD = 0.01


class SpeechToText:
    def __init__(self, mic_index: int = MIC_INDEX):
        self.mic_index = mic_index

        print("Loading Whisper model... (first time takes ~30 seconds)")
        self.model = WhisperModel("small", device="cpu", compute_type="int8")
        print("Whisper ready.")

    def listen_and_transcribe(self) -> str:
        print("Listening for command...")

        chunk_samples = int(CHUNK_SECONDS * NATIVE_RATE)
        max_chunks = int(MAX_RECORD_SECONDS / CHUNK_SECONDS)
        silence_chunks_needed = int(SILENCE_SECONDS_TO_STOP / CHUNK_SECONDS)

        chunks = []
        silent_chunks = 0
        started_speaking = False

        with sd.InputStream(
            samplerate=NATIVE_RATE,
            channels=1,
            dtype="float32",
            device=self.mic_index,
            blocksize=chunk_samples,
        ) as stream:
            for _ in range(max_chunks):
                audio_chunk, overflowed = stream.read(chunk_samples)

                if overflowed:
                    print("Audio status: input overflow")

                audio_flat = np.squeeze(audio_chunk)
                volume = np.sqrt(np.mean(audio_flat ** 2))

                chunks.append(audio_flat)

                if volume > SILENCE_THRESHOLD:
                    started_speaking = True
                    silent_chunks = 0
                elif started_speaking:
                    silent_chunks += 1

                if started_speaking and silent_chunks >= silence_chunks_needed:
                    break

        if not chunks:
            return ""

        audio_flat = np.concatenate(chunks)

        audio_16k = resample_poly(audio_flat, TARGET_RATE, NATIVE_RATE)

        segments, _ = self.model.transcribe(audio_16k, beam_size=1)
        text = " ".join(segment.text.strip() for segment in segments).strip()

        print(f"You said: {text}")
        return text