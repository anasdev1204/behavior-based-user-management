from pynput import keyboard
from typing import List, Optional

from src.utils.logging import setup_logging

import time, statistics, threading

logger = setup_logging("debug")

class KeyboardCapture:
    SENTENCE_TIMEOUT: int = 1

    def __init__(self):
        # The keystroke and shortcut lists will hold tuples where the values are ("key/shortcut", hold_time)
        self.current_pressed_keys_time: dict = {}

        self.keystroke: List[tuple[str, float]] = []
        self.shortcut: List[tuple[str, float]] = []

        self.shortcut_modifier_time: float = 0
        self.active_shortcut_keys: list[str] = []

        self.is_sentence: bool = False
        self.temp_start: float = 0
        self.temp_no_of_chars: int = 0
        self.last_key_time: float = 0
        self.reset_sentence_timer: Optional[threading.Timer] = None
        self.type_speed: List[float] = []

        self.listener: Optional[keyboard.Listener] = None
        self.is_running = False

    def start_capture(self):
        """Start capturing keyboard events in a separate thread"""
        if self.is_running:
            logger.warning("Capture already running")
            return

        self.is_running = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )

        self.listener.start()
        logger.info("Keyboard capture started")

    def monitor_typing_timeout(self):
        """Monitor for typing timeout in a separate thread"""
        while self.is_running:
            try:
                if self.is_sentence and time.time() - self.last_key_time > self.SENTENCE_TIMEOUT:
                    self._reset_typing_session()
                time.sleep(0.1)
            except KeyboardInterrupt:
                break

    def stop_capture(self):
        """Stop capturing mouse events"""
        if not self.is_running:
            logger.warning("Capture not running")
            return

        self.is_running = False
        if self.listener:
            self.listener.stop()
        logger.info("Keyboard capture stopped")

    def clear_data(self):
        """Clear all captured data"""
        self.keystroke.clear()
        self.shortcut.clear()
        self.type_speed.clear()
        logger.debug("All data cleared")

    @staticmethod
    def _key_to_string(key: keyboard.Key) -> str:
        """Convert key object to string representation"""
        try:
            if "Key" in str(key):
                return str(key).replace('Key.', '')
            else:
                return f"{key}"
        except AttributeError:
            return str(key)

    @staticmethod
    def _is_printable_char(key) -> bool:
        """Check if key represents a printable character"""
        try:
            return hasattr(key, 'char') and key.char is not None and key.char.isprintable()
        except AttributeError:
            return False

    def _is_shortcut_active(self, key: str) -> bool:
        """Detect if current pressed keys form a shortcut"""

        # Common modifier keys
        modifiers = {'ctrl_l', 'ctrl_r', 'alt_l', 'alt_gr', 'shift', 'shift_r', 'cmd', 'super'}
        is_modifier = key in modifiers
        if is_modifier:
            self.shortcut_modifier_time = time.time()

        return is_modifier

    def _start_timer(self):
        self.reset_sentence_timer = threading.Timer(self.SENTENCE_TIMEOUT, self._reset_typing_session)
        self.reset_sentence_timer.start()

    def _update_type_speed(self, key, current_time: float):
        """Update typing speed statistics"""
        if self._is_printable_char(key):
            if not self.is_sentence:
                self.is_sentence = True
                self.temp_start = current_time

            self.temp_no_of_chars += 1
            self.last_key_time = current_time
        else:
            self._reset_typing_session()

    def _reset_typing_session(self):
        """Reset typing speed measurement variables"""
        if self.is_sentence and self.temp_no_of_chars > 0:
            time_elapsed = time.time() - self.temp_start

            if time_elapsed > 0:
                chars_per_minute = (self.temp_no_of_chars / time_elapsed) * 60
                logger.debug(f"Sentence over! typing speed {chars_per_minute} cpm")
                self.type_speed.append(chars_per_minute)

        self.is_sentence = False
        self.temp_start = 0
        self.temp_no_of_chars = 0
        self.reset_sentence_timer = None

    def _on_press(self, key):
        """Handle keystroke press events"""
        key_str = self._key_to_string(key)
        if key_str in self.current_pressed_keys_time:
            return
        current_time = time.time()

        self.last_key_time = current_time
        self.current_pressed_keys_time[key_str] = current_time

        if (not self.is_sentence and self._is_shortcut_active(key_str)) or len(self.active_shortcut_keys) > 0:
            self.active_shortcut_keys.append(key_str)
        else:
            self._update_type_speed(key, current_time)

    def _on_release(self, key):
        """Handle keystroke release events"""
        current_time = time.time()
        key_str = self._key_to_string(key)

        if key_str in self.current_pressed_keys_time:
            hold_time = current_time - self.current_pressed_keys_time[key_str]

            if len(self.active_shortcut_keys) > 0:
                hold_time = current_time - self.shortcut_modifier_time
                full_shortcut = "+".join(self.active_shortcut_keys)
                logger.debug(f"Shortcut done: {full_shortcut}")
                self.shortcut.append((full_shortcut, hold_time))
                for key in self.active_shortcut_keys:
                    del self.current_pressed_keys_time[key]
                self.active_shortcut_keys.clear()
            else:
                self.keystroke.append((key_str, hold_time))
                del self.current_pressed_keys_time[key_str]

    # Statistic methods

    def _get_keystroke_stats(self) -> dict:
        """Get statistics about keystrokes"""
        if not self.keystroke and not self.shortcut:
            return {"message": "No movement data recorded"}

        def summarize(data: list[tuple[str, float]]) -> dict:
            stats = {}
            for key_str, hold_time in data:
                stats.setdefault(key_str, []).append(hold_time)

            return {
                k: {
                    "avg_hold_time": sum(v) / len(v),
                    "no_of_uses": len(v)
                }
                for k, v in stats.items()
            }

        keystrokes_summary = summarize(self.keystroke)
        shortcuts_summary = summarize(self.shortcut)

        # flatten all hold times
        all_hold_times = [ht for _, ht in self.keystroke + self.shortcut]

        overall_avg = sum(all_hold_times) / len(all_hold_times) if all_hold_times else 0

        return {
            "keys": keystrokes_summary,
            "shortcuts": shortcuts_summary,
            "overall": {
                "avg_hold_time": overall_avg,
                "total_presses": len(all_hold_times)
            }
        }

    def _get_type_speed_stats(self) -> dict:
        """Get statistics about type-speed"""
        return {
            "total_kb_sessions": len(self.type_speed),
            "avg_cpm": round(statistics.mean(self.type_speed), 2) if self.type_speed else 0,
            "median_cpm": round(statistics.median(self.type_speed), 2) if self.type_speed else 0,
            "min_cpm": round(min(self.type_speed), 2) if self.type_speed else 0,
            "max_cpm": round(max(self.type_speed), 2) if self.type_speed else 0,
            "std_deviation": round(statistics.stdev(self.type_speed) if len(self.type_speed) > 1 else 0, 2),
            "all_kb_sessions_cpm": [round(speed, 2) for speed in self.type_speed] if self.type_speed else 0,
        }

    def get_summary(self) -> dict:
        """Get a summary of all captured data"""
        return {
            "keystrokes": self._get_keystroke_stats(),
            "type_speed": self._get_type_speed_stats()
        }