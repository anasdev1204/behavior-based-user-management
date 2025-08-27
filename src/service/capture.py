from src.capture.mouse_capture import MouseCapture
from src.capture.kb_capture import KeyboardCapture

from src.utils.storage import EventStore
from src.utils.config import load_config, ensure_dirs
from src.utils.logging import setup_logging

import threading, time, uuid, logging

def print_statistics(logger: logging.Logger, summary: dict, source: str):
    """
    Prints statistics about the capture
    :param logger: logger object
    :param summary: summary dictionary
    :param source: source
    :return:
    """
    logger.info("=" * 50)
    logger.info(f"{source} ACTIVITY SUMMARY")
    logger.info("=" * 50)

    for category, stats in summary.items():
        logger.info(f"\n{category.upper()}:")
        for key, value in stats.items():
            if isinstance(value, float):
                logger.info(f"  {key}: {value:.2f}")
            else:
                logger.info(f"  {key}: {value}")

def main():
    cfg = load_config("config.yaml")
    ensure_dirs(cfg)

    logger = setup_logging("logs")

    start_time = time.time()
    mouse_capture = MouseCapture()
    mouse_capture.start_capture()

    kb_capture = KeyboardCapture()
    kb_capture.start_capture()
    timeout_thread = threading.Thread(target=kb_capture.monitor_typing_timeout, daemon=True)
    timeout_thread.start()

    logger.info("Mouse capture running... Press Ctrl+C to stop")
    logger.info("Keyboard capture running... Press Ctrl+C to stop")

    try:
        while kb_capture.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.warning("Stopping capture...")
    finally:
        mouse_capture.stop_capture()
        mouse_summary = mouse_capture.get_summary()
        logger.info("Mouse summary collected")
        print_statistics(logger, mouse_summary, "MOUSE")
        kb_capture.stop_capture()
        kb_summary = kb_capture.get_summary()
        logger.info("Keyboard summary collected")
        print_statistics(logger, kb_summary, "KEYBOARD")

        store = EventStore(cfg["paths"]["db_path"])
        session_id = str(uuid.uuid4())
        store.upsert_session(
            session_id=session_id,
            context="capture",
            start_ts_ns=start_time,
            end_ts_ns=int(time.time()),
        )

        store.upsert_mouse_data(
            session_id=session_id,
            avg_dx=mouse_summary.get("movement", {}).get("avg_dx"),
            avg_dy=mouse_summary.get("movement", {}).get("avg_dy"),
            avg_scroll_distance=mouse_summary.get("scroll", {}).get("avg_scroll_distance"),
            avg_click_interval=mouse_summary.get("click", {}).get("avg_click_interval"),
            clicks_per_minute=mouse_summary.get("click", {}).get("clicks_per_minute"),
        )

        store.upsert_kb_data(
            session_id=session_id,
            avg_cpm=kb_summary.get("type_speed", {}).get("avg_cpm"),
            median_cpm=kb_summary.get("type_speed", {}).get("median_cpm"),
            avg_hold_time=kb_summary.get("keystrokes", {}).get("overall", {}).get("avg_hold_time"),
        )

        store.upsert_key_stats(
            session_id=session_id,
            keys=kb_summary["keystrokes"]["keys"],
            shortcuts=kb_summary["keystrokes"]["shortcuts"],
        )



if __name__ == "__main__":
    main()
