from components.wake_word import WakeWordListener

def main():
    wake = WakeWordListener(
        mic_index=24,
        threshold=0.5,
        vad_threshold=0.3,
        enable_speex_noise_suppression=False,
        wakeword_models=None,
    )

    while True:
        detected = wake.wait_for_wake_word()
        print(f"Detected: {detected}")


if __name__ == "__main__":
    main()
