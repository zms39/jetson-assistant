import subprocess
import os
from math import gcd

import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from scipy.signal import resample_poly

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_PROJECT_ROOT, "models", "en_US-lessac-medium.onnx")

# Speaker device index
def _find_speaker_index():
    for i, dev in enumerate(sd.query_devices()):
        if 'usb' in dev['name'].lower() and dev['max_output_channels'] > 0:
            return i
    return None  # no USB speaker found: fall back to system default output
SPEAKER_INDEX = _find_speaker_index()

if SPEAKER_INDEX is not None:
    print(f"[tts] Using USB audio output: {sd.query_devices(SPEAKER_INDEX)['name']}")
else:
    print("[tts] No USB audio output found; using system default output")


class TextToSpeech:
    def speak(self, text, on_start=None):
        print(f"Speaking: {text}")
        output_file = "/tmp/response.wav"

        # Generate audio file using Piper
        process = subprocess.run(
            ["piper", "--model", MODEL_PATH, "--output_file", output_file],
            input=text.encode(),
            capture_output=True
        )

        if os.path.exists(output_file):
            self._play_wav(output_file, on_start)
        else:
            print("TTS failed:", process.stderr.decode())

    def _play_wav(self, path, on_start=None):
        try:
            rate, audio = wavfile.read(path)

            # Measure the *spoken* span, not the full clip: Piper pads the WAV
            # with silence at both ends, which would otherwise make the text
            # pace itself over dead air and lag behind the voice.
            mono = audio if audio.ndim == 1 else audio[:, 0]
            amp = np.abs(mono.astype(np.float32))
            threshold = amp.max() * 0.02   # 2% of peak = speech vs. silence
            loud = np.where(amp > threshold)[0]
            if len(loud) > 0:
                duration = (loud[-1] - loud[0]) / rate
            else:
                duration = len(audio) / rate  # silent clip: fall back to full length

            # (existing format-check / resample-to-stereo block stays here unchanged)
            try:
                sd.check_output_settings(device=SPEAKER_INDEX, samplerate=rate, channels=1)
            except Exception:
                dev = sd.query_devices(SPEAKER_INDEX, 'output')
                target_rate = int(dev['default_samplerate'])
                if target_rate != rate:
                    g = gcd(target_rate, rate)
                    audio = resample_poly(audio, target_rate // g, rate // g)
                    audio = np.clip(audio, -32768, 32767).astype(np.int16)
                    rate = target_rate
                if dev['max_output_channels'] >= 2:
                    audio = np.column_stack([audio, audio])

            # Tell the caller how long the speech is, the instant before it starts
            if on_start:
                on_start(duration)

            channels = audio.shape[1] if audio.ndim > 1 else 1
            sd.stop()  # release any stream still held from the previous utterance
            with sd.OutputStream(samplerate=rate, device=SPEAKER_INDEX,
                                 channels=channels, dtype='int16',
                                 blocksize=2048, latency='high') as stream:
                stream.write(audio)

        except Exception as e:
            print(f"[tts] sounddevice playback failed ({e}); falling back to aplay")
            if on_start:
                # Fallback path: estimate duration so the display still paces itself
                try:
                    rate, audio = wavfile.read(path)
                    on_start(len(audio) / rate)
                except Exception:
                    on_start(None)
            subprocess.run(["aplay", path])