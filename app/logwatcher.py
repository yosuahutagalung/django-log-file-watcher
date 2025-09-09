import asyncio
import os
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async
from .models import LogFile


class LogHandler(FileSystemEventHandler):
    def __init__(self, filepath, log_id, encoding='utf-8'):
        self.filepath = filepath
        self.log_id = log_id
        self.encoding = encoding
        self._pos = 0
        self.channel_layer = get_channel_layer()

    def on_modified(self, event):
        if event.src_path == self.filepath:
            try:
                file_size = os.path.getsize(self.filepath)

                # Handle truncation or rotation
                if file_size < self._pos:
                    self._pos = 0

                with open(self.filepath, "r", encoding=self.encoding) as f:
                    f.seek(self._pos)
                    for line in f:
                        async_to_sync(self.channel_layer.group_send)(
                            f"logs_{self.log_id}",
                            {"type": "log_message", "line": line.strip()},
                        )
                    self._pos = f.tell()

            except FileNotFoundError:
                pass


class LogManager:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}  # log_file_id -> (handler, watch)
        self.lock = threading.Lock()
        self._started = False

    def start_all(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._start_all_sync()
        else:
            asyncio.create_task(self._start_all_async())

    def _start_all_sync(self):
        log_files = list(LogFile.objects.all())
        for lf in log_files:
            self.start_watcher(lf)
        with self.lock:
            if not self._started:
                self.observer.start()
                self._started = True

    async def _start_all_async(self):
        log_files = await sync_to_async(list)(LogFile.objects.all())
        for lf in log_files:
            self.start_watcher(lf)
        with self.lock:
            if not self._started:
                self.observer.start()
                self._started = True

    def start_watcher(self, log_file):
        with self.lock:
            if log_file.id in self.handlers:
                return

            if not os.path.exists(log_file.path):
                print(f"⚠️ Skipping {log_file.path}, file does not exist yet.")
                return

            handler = LogHandler(log_file.path, log_file.id, getattr(log_file, "encoding", "utf-8"))
            watch = self.observer.schedule(handler, os.path.dirname(log_file.path), recursive=False)
            self.handlers[log_file.id] = (handler, watch)

    def stop_watcher(self, log_file):
        self.stop_watcher_by_id(log_file.id)

    def stop_watcher_by_id(self, log_file_id):
        with self.lock:
            entry = self.handlers.pop(log_file_id, None)
        if entry:
            handler, watch = entry
            try:
                self.observer.unschedule(watch)
            except Exception as e:
                print(f"⚠️ Failed to unschedule watcher {log_file_id}: {e}")

    def refresh(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._refresh_sync()
        else:
            asyncio.create_task(self._refresh_async())

    def _refresh_sync(self):
        existing_ids = set(LogFile.objects.values_list("id", flat=True))

        for logfile_id in list(self.handlers.keys()):
            if logfile_id not in existing_ids:
                self.stop_watcher_by_id(logfile_id)

        for lf in LogFile.objects.all():
            if lf.id not in self.handlers:
                self.start_watcher(lf)

    async def _refresh_async(self):
        existing_ids = set(await sync_to_async(list)(LogFile.objects.values_list("id", flat=True)))
        for logfile_id in list(self.handlers.keys()):
            if logfile_id not in existing_ids:
                self.stop_watcher_by_id(logfile_id)

        log_files = await sync_to_async(list)(LogFile.objects.all())
        for lf in log_files:
            if lf.id not in self.handlers:
                self.start_watcher(lf)

    def stop_all(self):
        """Stop all watchers and shutdown observer cleanly."""
        with self.lock:
            for logfile_id in list(self.handlers.keys()):
                self.stop_watcher_by_id(logfile_id)

        if self._started:
            self.observer.stop()
            self.observer.join()
            self._started = False


log_manager = LogManager()

# single shared manager instance
log_manager = LogManager()