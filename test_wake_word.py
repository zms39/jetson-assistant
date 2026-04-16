from components.wake_word import WakeWordListener
import time

def main():
    wake = WakeWordListener(
        mic_index=24,
        threshold=0.5,
        vad_threshold=0.3,
    )

    while True:
        detected = wake.wait_for_wake_word()
        print(f"Detected: {detected}")
        time.sleep(2.0)

if __name__ == "__main__":
    main()