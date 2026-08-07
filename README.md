# Retro PC AI Assistant

## An on-device AI voice assistant for the NVIDIA Jetson Orin Nano.

A retro-inspired, fully local AI voice assistant built on the NVIDIA Jetson Orin Nano. Housed in a wood-textured 3D-printed enclosure, it listens for one of the following wake words:

* "Alexa"
* "Hey Mycroft"
* "Hey Jarvis"
* "Hey Rhasspy"
* "What's the weather"
* "Set a 10 minute timer"

However, for the themeing of the device, the model is prompted to believe it's name is Jarvis and the user is expected to say "Hey Jarvis" to begin an interaction.

Afterwards, it transcribes your speech query locally: speech is transcribed on-device by Whisper, the text is passed to the llama3.2:3b model via Ollama to generate a reply, and the response is spoken aloud with Piper while being typed out on the display before returning to an idle animation. When connected to the internet and a question needs current or factual information, the LLM calls a web-search tool (DuckDuckGo) and answers from the results. The model is also equipped with a memory for recent conversations across turns and persists between restarts.

## Architecture

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/architectureDark.png">
  <source media="(prefers-color-scheme: light)" srcset="assets/architectureLight.png">
  <img alt="Jetson Assistant Architecture" src="assets/architectureLight.png">
</picture>

# Installation

## Prerequisites

- Micro sd card with _Jetson Orin Nano Developer Kit on JetPack 6.x_ download
- A USB microphone
- A USB audio output for the speakers
- Git LFS
```bash
sudo apt install git-lfs
```

- Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

## 1. Clone Git Repository

```bash
git clone https://github.com/zms39/jetson-assistant.git
cd jetson-assistant

# Download the Piper voice model (~63 MB)
git lfs install
git lfs pull
```

## 2. Set Up the Python Environment

```bash
sudo apt install python3.10-venv portaudio19-dev libportaudio2
python3 -m venv venv
source venv/bin/activate
pip install "numpy==1.26.4" faster-whisper openwakeword sounddevice scipy requests pygame piper-tts ddgs
```

NumPy is pinned below 2.0 for compatibility with `tflite_runtime` (used by openWakeWord). PortAudio is the system audio backend `sounddevice` needs.

## 3. Run the Program

From the project root with the venv active:

```bash
python main.py
```

Or use the launcher, which activates the venv for you:

```bash
./start.sh
```

`main.py` waits for Ollama, warms up the model, loads Whisper and the wake-word models, then enters idle. 

Function Controls: 
- `ESC` exits to the desktop
- `A` toggles dot-matrix art mode 
  - Alternatively, you can say "art mode", "art", "screensaver", "show art", "display art", "dot matrix" during the listening phase.
- `N` cycles dot-matrix animations. 
- Say "forget everything" during the listening phase to clear conversation memory.

## 4. Optional Auto-start on boot

To boot straight into the assistant:

1. Enable Automatic Login in Settings → Users.
2. Copy the autostart entry into place:

```bash
mkdir -p ~/.config/autostart
cp jetson-assistant.desktop ~/.config/autostart/
```

*Note: Edit the `Exec=` path in that file if your username or repo location differs.*

On boot the desktop launches a terminal running `start.sh`, so startup logs are visible and `ESC` still drops to the desktop.

## Known Issues
- The system is version-locked to Jetson Linux 36.4.4; the `nvidia-l4t-*` packages are held (`apt-mark hold`) to prevent an upgrade to a release with a known CUDA allocation bug. Do not remove those holds lest you tempt fate.