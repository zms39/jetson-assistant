import sys
sys.path.insert(0, '/home/youruser/assistant')
from components.tts import TextToSpeech

tts = TextToSpeech()
tts.speak("Hello, I am your voice assistant. How can I help you today?")
