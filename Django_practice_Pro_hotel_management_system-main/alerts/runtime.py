import logging
import os
import sys
import threading

from django.conf import settings
from django.db import close_old_connections

from .notifications import dispatch_pending_alert_notifications
from .services import refresh_simulated_readings


logger = logging.getLogger(__name__)

_monitor_thread = None
_monitor_lock = threading.Lock()


def run_monitoring_cycle(*, force_refresh=False):
    refreshed = refresh_simulated_readings(force=force_refresh)
    notification_summary = dispatch_pending_alert_notifications()
    return {
        "refreshed_readings": len(refreshed),
        **notification_summary,
    }


class IoTMonitorThread(threading.Thread):
    def __init__(self, interval_seconds):
        super().__init__(name="iot-monitor-loop", daemon=True)
        self.interval_seconds = max(int(interval_seconds), 15)
        self.stop_event = threading.Event()

    def run(self):
        logger.info("Starting IoT monitoring loop with %s second interval.", self.interval_seconds)
        while not self.stop_event.is_set():
            close_old_connections()
            try:
                run_monitoring_cycle(force_refresh=False)
            except Exception:
                logger.exception("IoT monitoring loop failed during cycle execution.")
            finally:
                close_old_connections()

            self.stop_event.wait(self.interval_seconds)


def should_autostart_monitor():
    if not getattr(settings, "IOT_MONITOR_AUTOSTART", settings.DEBUG):
        return False

    blocked_commands = {"makemigrations", "migrate", "collectstatic", "shell", "dbshell", "test", "run_iot_monitor"}
    if any(command in sys.argv for command in blocked_commands):
        return False

    if settings.DEBUG and "runserver" not in sys.argv:
        return False

    if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
        return False

    return True


def start_monitor_thread():
    global _monitor_thread

    if not should_autostart_monitor():
        return None

    with _monitor_lock:
        if _monitor_thread and _monitor_thread.is_alive():
            return _monitor_thread

        _monitor_thread = IoTMonitorThread(getattr(settings, "IOT_MONITOR_INTERVAL_SECONDS", 30))
        _monitor_thread.start()
        return _monitor_thread
