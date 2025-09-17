from pynput import mouse
from typing import List, Tuple, Optional

from src.utils.logging import setup_logging

import time, statistics, threading

logger = setup_logging("debug")

class MouseCapture:

    SCROLL_INTERVAL = 1

    def __init__(self):
        self.move_dx: List[float] = []
        self.move_dy: List[float] = []
        self.last_move_x: float = 0
        self.last_move_y: float = 0

        self.is_scrolling: bool = False
        self.temp_scroll: int = 0
        self.scroll_dy: List[float] = []

        self.click_times: List[float] = []
        self.click_positions: List[Tuple[float, float]] = []
        self.click_button: dict = {}

        self.listener: Optional[mouse.Listener] = None
        self.is_running = False

    def start_capture(self):
        """Start capturing mouse events in a separate thread"""
        if self.is_running:
            logger.warning("Capture already running")
            return

        self.is_running = True
        self.listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )

        self.listener.start()
        logger.info("Mouse capture started")

    def stop_capture(self):
        """Stop capturing mouse events"""
        if not self.is_running:
            logger.warning("Capture not running")
            return

        self.listener.stop()
        self.is_running = False
        logger.info("Mouse capture stopped")

    def clear_data(self):
        """Clear all captured data"""
        self.move_dx.clear()
        self.move_dy.clear()
        self.scroll_dy.clear()
        self.click_times.clear()
        self.click_positions.clear()
        logger.debug("All data cleared")

    def _update_move_stats(self, last_move_x: float, last_move_y: float,
                           new_move_dx: float, new_move_dy: float):
        """Update movement statistics"""
        self.last_move_x = last_move_x
        self.last_move_y = last_move_y

        self.move_dx.append(new_move_dx)
        self.move_dy.append(new_move_dy)

    def _on_move(self, x: float, y: float):
        """Handle mouse movement events"""
        local_dx = abs(x - self.last_move_x)
        local_dy = abs(y - self.last_move_y)

        if local_dx > 0 or local_dy > 0:
            self._update_move_stats(x, y, local_dx, local_dy)

    def _update_scroll_stats(self):
        """Update scroll statistics"""
        logger.debug("Scroll event over")
        self.scroll_dy.append(self.temp_scroll)
        self.temp_scroll = 0
        self.is_scrolling = False

    def _on_scroll(self, _x: float, _y: float, _dx: float, _dy: float):
        """Handle mouse scroll events"""
        if not self.is_scrolling and self.temp_scroll == 0:
            logger.debug("Scroll event detected")
            self.is_scrolling = True
            timer = threading.Timer(self.SCROLL_INTERVAL, self._update_scroll_stats)
            timer.start()

        self.temp_scroll += 1

    def _on_click(self, x: float, y: float, button: mouse.Button, pressed: bool):
        """Handle mouse click events"""
        if pressed:
            current_time = time.time()
            self.click_times.append(current_time)
            self.click_positions.append((x, y))

            button_name = str(button)

            if  self.click_button.get(button_name):
                self.click_button[button_name] += 1
            else:
                self.click_button[button_name] = 1

            logger.debug(f"Click: {button} at ({x}, {y})")


    # Statistic methods

    def _get_movement_stats(self) -> dict:
        """Get statistics about mouse movement"""
        if not self.move_dx or not self.move_dy:
            return {"message": "No movement data recorded"}

        return {
            "total_movements": len(self.move_dx),
            "avg_dx": statistics.mean(self.move_dx),
            "avg_dy": statistics.mean(self.move_dy),
            "max_dx": max(self.move_dx),
            "max_dy": max(self.move_dy),
            "total_distance": sum(self.move_dx) + sum(self.move_dy)
        }

    def _get_scroll_stats(self) -> dict:
        """Get statistics about mouse scrolling"""
        if not self.scroll_dy:
            return {"message": "No scroll data recorded"}

        return {
            "total_scrolls": len(self.scroll_dy),
            "total_scroll_distance": sum(abs(y) for y in self.scroll_dy),
            "avg_scroll_distance": statistics.mean(self.scroll_dy),
        }

    def _get_click_stats(self) -> dict:
        """Get statistics about mouse clicks"""

        click_intervals = []
        for i in range(1, len(self.click_times)):
            interval = self.click_times[i] - self.click_times[i - 1]
            click_intervals.append(interval)

        return {
            "total_clicks": len(self.click_times),
            "avg_click_interval": statistics.mean(click_intervals) if click_intervals else 0,
            "clicks_per_minute": len(self.click_times) / ((self.click_times[-1] - self.click_times[0]) / 60)
            if len(self.click_times) > 1 else 0,
            "clicks_per_button": self.click_button
        }

    def get_summary(self) -> dict:
        """Get a summary of all captured data"""
        return {
            "movement": self._get_movement_stats(),
            "scroll": self._get_scroll_stats(),
            "click": self._get_click_stats()
        }