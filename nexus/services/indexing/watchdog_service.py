"""
NEXUS Watchdog -- detects file changes and adds indexing jobs to Redis queue.

Watches the watch_paths defined in nexus.config.yaml.
"""

import json
import logging
import os
import time
from pathlib import Path
from threading import Timer

import redis
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from utils.config_loader import get_indexing_config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger("nexus.watchdog")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
QUEUE_NAME = "nexus:indexing:queue"

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".csv",
    ".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml",
    ".html", ".htm",
}


class FileEventDebouncer:
    """File event debouncer -- merges repeated events within a short time window into one."""

    def __init__(self, delay: float, callback):
        self._delay = delay
        self._callback = callback
        self._timers: dict[str, Timer] = {}

    def trigger(self, file_path: str):
        if file_path in self._timers:
            self._timers[file_path].cancel()

        timer = Timer(self._delay, self._fire, args=[file_path])
        self._timers[file_path] = timer
        timer.start()

    def _fire(self, file_path: str):
        self._timers.pop(file_path, None)
        self._callback(file_path)


class NexusFileHandler(FileSystemEventHandler):
    """Handles file create/modify/delete events."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        config = get_indexing_config()
        debounce_sec = config.get("debounce_seconds", 5)
        self.debouncer = FileEventDebouncer(debounce_sec, self._enqueue)

    def _is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _enqueue(self, file_path: str):
        """Add indexing job to Redis queue."""
        task = {"file_path": file_path, "retries": 0, "event": "modified"}
        self.redis.lpush(QUEUE_NAME, json.dumps(task))
        logger.info(f"Queued: {file_path}")

    def on_created(self, event):
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            self.debouncer.trigger(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            self.debouncer.trigger(event.src_path)

    def on_deleted(self, event):
        if event.is_directory:
            return
        if self._is_supported(event.src_path):
            task = {"file_path": event.src_path, "retries": 0, "event": "deleted"}
            self.redis.lpush(QUEUE_NAME, json.dumps(task))
            logger.info(f"Queued (delete): {event.src_path}")


def main():
    config = get_indexing_config()
    watch_paths = config.get("watch_paths", ["/documents"])

    redis_client = redis.from_url(REDIS_URL)
    handler = NexusFileHandler(redis_client)
    observer = Observer()

    for watch_path in watch_paths:
        path = Path(watch_path)
        if path.exists():
            observer.schedule(handler, str(path), recursive=True)
            logger.info(f"Watching: {watch_path}")
        else:
            logger.warning(f"Watch path not found: {watch_path}")

    observer.start()
    logger.info("Watchdog started. Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    logger.info("Watchdog stopped.")


if __name__ == "__main__":
    main()
