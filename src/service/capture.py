from src.features.mouse_capture import MouseCapture
from src.features.kb_capture import KeyboardCapture


import threading, time

def print_statistics(summary: dict, source: str):
    """
    Prints statistics about the capture
    :param summary: summary dictionary
    :param source: source
    :return:
    """
    print("\n" + "=" * 50)
    print(f" {source} ACTIVITY SUMMARY")
    print("=" * 50)

    for category, stats in summary.items():
        print(f"\n{category.upper()}:")
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: {value}")


def main():
    mouse_capture = MouseCapture()
    mouse_capture.start_capture()
    print("Mouse capture running... Press Ctrl+C to stop")

    kb_capture = KeyboardCapture()
    kb_capture.start_capture()
    timeout_thread = threading.Thread(target=kb_capture.monitor_typing_timeout, daemon=True)
    timeout_thread.start()
    print("Keyboard capture running...Press Ctrl+C to stop")

    try:
        while kb_capture.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping capture...")
    finally:
        mouse_capture.stop_capture()
        print_statistics(mouse_capture.get_summary(), "MOUSE")
        kb_capture.stop_capture()
        print_statistics(kb_capture.get_summary(), "KEYBOARD")

if __name__ == "__main__":
    main()
