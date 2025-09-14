import threading
import time
import sys
import subprocess
import platform


class WindowCapture:
    def __init__(self, window_poll_interval=0.5):
        self.window_poll_interval = window_poll_interval

        self.running = False
        self.current_context = None
        self.session_start = None

    def run(self, on_window_change):
        """
        on_window_change: function that takes one argument (context string)
        """
        self.running = True
        prev_context = None

        try:
            while self.running:
                active_window = self.get_active_window()
                context = f"{active_window}"

                if context != prev_context:
                    prev_context = context
                    on_window_change(context)

                time.sleep(self.window_poll_interval)
        except KeyboardInterrupt:
            print("\n[!] Stopping capture...")
            sys.exit(0)

    @staticmethod
    def get_active_window():
        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                script = '''
                    tell application "System Events"
                        set frontApp to name of first process whose frontmost is true
                    end tell
                    return frontApp
                '''
                active_window = subprocess.check_output(["osascript", "-e", script]).decode().strip()
                return active_window

        except Exception:
            pass
        return "unknown", "no-title"