import sys
sys.path.insert(0, '/home/youruser/assistant')  # replace youruser with your username
from components.stt import SpeechToText

stt = SpeechToText()
while True:
    text = stt.listen_and_transcribe()
    print("Transcribed:", text)
    input("Press Enter to listen again...")
