from src.capture.mouse_capture import MouseCapture
from src.capture.kb_capture import KeyboardCapture
from src.capture.window_capture import WindowCapture

from src.utils.storage import EventStore
from src.utils.config import load_config, ensure_dirs
from src.utils.logging import setup_logging

import time, uuid, threading

class CaptureManager:
    def __init__(self, cfg):

        self.kb = KeyboardCapture()
        self.mouse = MouseCapture()
        self.session_start = None
        self.current_context = None
        self.logger = setup_logging("logs")
        self.store = EventStore(cfg["paths"]["db_path"], self.logger)

    def on_window_change(self, context):
        if self.current_context is not None:
            self.end_session()

        self.current_context = context
        self.session_start = time.time()
        self.mouse.start_capture()
        self.kb.start_capture()
        threading.Thread(target=self.kb.monitor_typing_timeout, daemon=True).start()


    def end_session(self):
        self.kb.stop_capture()
        self.mouse.stop_capture()
        kb_summary = self.kb.get_summary()
        mouse_summary = self.mouse.get_summary()

        self.logger.info(f"[+] Ending session {self.current_context}")

        self.logger.info("Mouse summary collected")
        self.log_statistics(mouse_summary, "MOUSE")
        self.logger.info("Keyboard summary collected")
        self.log_statistics(kb_summary, "KEYBOARD")


        session_id = str(uuid.uuid4())
        self.store.upsert_session(
            session_id=session_id,
            context=f"capture - {self.current_context}",
            start_ts_ns=self.session_start,
            end_ts_ns=int(time.time()),
        )

        self.logger.info("Session inserted")

        self.store.upsert_mouse_data(
            session_id=session_id,
            avg_dx=mouse_summary.get("movement", {}).get("avg_dx"),
            avg_dy=mouse_summary.get("movement", {}).get("avg_dy"),
            avg_scroll_distance=mouse_summary.get("scroll", {}).get("avg_scroll_distance"),
            avg_click_interval=mouse_summary.get("click", {}).get("avg_click_interval"),
            clicks_per_minute=mouse_summary.get("click", {}).get("clicks_per_minute"),
        )

        self.logger.info("Mouse data inserted")

        self.store.upsert_kb_data(
            session_id=session_id,
            avg_cpm=kb_summary.get("type_speed", {}).get("avg_cpm"),
            median_cpm=kb_summary.get("type_speed", {}).get("median_cpm"),
            avg_hold_time=kb_summary.get("keystrokes", {}).get("overall", {}).get("avg_hold_time"),
        )

        self.logger.info("Keyboard data inserted")

        self.store.upsert_key_stats(
            session_id=session_id,
            keys=kb_summary["keystrokes"]["keys"],
            shortcuts=kb_summary["keystrokes"]["shortcuts"],
        )

        self.current_context = None
        self.session_start = None

    def log_statistics(self, summary: dict, source: str):
        """
        Logs statistics about the capture
        :param summary: summary dictionary
        :param source: source
        :return:
        """
        self.logger.info("=" * 50)
        self.logger.info(f"{source} ACTIVITY SUMMARY")
        self.logger.info("=" * 50)

        for category, stats in summary.items():
            self.logger.info(f"\n{category.upper()}:")
            for key, value in stats.items():
                if isinstance(value, float):
                    self.logger.info(f"  {key}: {value:.2f}")
                else:
                    self.logger.info(f"  {key}: {value}")


if __name__ == "__main__":
    cfg = load_config("config.yaml")
    ensure_dirs(cfg)

    wc = WindowCapture(window_poll_interval=float(cfg["capture"]["window_poll_interval"]))
    cm = CaptureManager(cfg)
    wc.run(cm.on_window_change)


