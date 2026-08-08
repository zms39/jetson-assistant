import subprocess
import os
import re

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_PROJECT_ROOT, "models", "en_US-lessac-medium.onnx")


# Speaker device selection -------------------------------------------------
def _find_speaker_index():
    """Index of the USB audio adapter, matched by name for stability."""
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if 'usb audio device' in dev['name'].lower() and dev['max_output_channels'] > 0:
            return i
    for i, dev in enumerate(devices):  # fallback: any USB output
        if 'usb' in dev['name'].lower() and dev['max_output_channels'] > 0:
            return i
    return None


def _find_speaker_hw():
    """ALSA hw string (e.g. '1,0') for the USB adapter, parsed from its name.

    Playback goes through `aplay -D plughw:<hw>` because the raw sounddevice
    OutputStream stalls on this adapter, while aplay via plughw (which lets
    ALSA convert the format) plays cleanly. The card number shifts between
    boots, so it is derived at runtime rather than hardcoded.
    """
    for dev in sd.query_devices():
        name = dev['name']
        if 'usb audio device' in name.lower() and dev['max_output_channels'] > 0:
            m = re.search(r'hw:(\d+,\d+)', name)
            if m:
                return m.group(1)
    return None


SPEAKER_INDEX = _find_speaker_index()
SPEAKER_HW = _find_speaker_hw()

if SPEAKER_INDEX is not None:
    print(f"[tts] Using USB audio output: {sd.query_devices(SPEAKER_INDEX)['name']}")
else:
    print("[tts] No USB audio output found; using system default output")


class TextToSpeech:
    def speak(self, text, on_start=None):
        print(f"Speaking: {text}")
        output_file = "/tmp/response.wav"

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

            # Measure the spoken span (silence-trimmed) so the display can pace
            # the text reveal to the actual speech length.
            mono = audio if audio.ndim == 1 else audio[:, 0]
            amp = np.abs(mono.astype(np.float32))
            peak = amp.max()
            if peak > 0:
                loud = np.where(amp > peak * 0.02)[0]
                duration = (loud[-1] - loud[0]) / rate if len(loud) > 0 else len(audio) / rate
            else:
                duration = len(audio) / rate

            if on_start:
                on_start(duration)

            # Play through ALSA. plughw lets ALSA auto-convert the mono 22050 Hz
            # Piper output to whatever the adapter wants; this is reliable where
            # the sounddevice OutputStream stalls.
            if SPEAKER_HW is not None:
                subprocess.run(["aplay", "-D", f"plughw:{SPEAKER_HW}", path])
            else:
                subprocess.run(["aplay", path])

        except Exception as e:
            print(f"[tts] playback failed ({e}); trying default aplay")
            if on_start:
                try:
                    rate, audio = wavfile.read(path)
                    on_start(len(audio) / rate)
                except Exception:
                    on_start(None)
            subprocess.run(["aplay", path])