import subprocess
import os

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_PROJECT_ROOT, "models", "en_US-lessac-medium.onnx")

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
            # Play through default audio output
            subprocess.run(["aplay", output_file])
        else:
            print("TTS failed:", process.stderr.decode())
