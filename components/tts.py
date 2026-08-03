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
    def speak(self, text):
        print(f"Speaking: {text}")
        output_file = "/tmp/response.wav"

        # Generate audio file using Piper
        process = subprocess.run(
            ["piper", "--model", MODEL_PATH, "--output_file", output_file],
            input=text.encode(),
            capture_output=True
        )

        if os.path.exists(output_file):
            self._play_wav(output_file)
        else:
            print("TTS failed:", process.stderr.decode())

    def _play_wav(self, path):
        try:
            rate, audio = wavfile.read(path)

            # Piper outputs mono 22050 Hz. If the output device rejects
            # that format, convert to the device's native rate / stereo.
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

            sd.play(audio, rate, device=SPEAKER_INDEX)
            sd.wait()

        except Exception as e:
            # Last resort: hand the file to ALSA directly
            print(f"[tts] sounddevice playback failed ({e}); falling back to aplay")
            subprocess.run(["aplay", path])