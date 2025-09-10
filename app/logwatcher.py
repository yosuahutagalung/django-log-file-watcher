import asyncio
import os
import threading

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async
from watchdog.observers.polling import PollingObserver

from .models import LogFile


class LogHandler:
    def __init__(self, filepath, log_id, encoding="utf-8"):
        self.filepath = filepath
        self.log_id = log_id
        self.encoding = encoding
        self._pos = 0
        self.channel_layer = get_channel_layer()

    def process_file(self):
        try:
            file_size = os.path.getsize(self.filepath)

            # Handle truncation/rotation
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


class DirectoryHandler(FileSystemEventHandler):
    def __init__(self, handlers):
        # handlers: {filepath: LogHandler}
        self.handlers = handlers

    def on_modified(self, event):
        if event.is_directory:
            return
        handler = self.handlers.get(event.src_path)
        if handler:
            handler.process_file()


class LogManager:
    """Manages all directory/file watchers with safe async/sync usage."""

    def __init__(self):
        self.observer = PollingObserver(timeout=0.5)
        self.dir_handlers = {}   # {directory: (DirectoryHandler, watch)}
        self.file_handlers = {}  # {log_file_id: LogHandler}
        self.lock = threading.Lock()
        self._started = False

    # ---------- START ----------
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

    # ---------- WATCHERS ----------
    def start_watcher(self, log_file):
        with self.lock:
            if log_file.id in self.file_handlers:
                return

            if not os.path.exists(log_file.path):
                print(f"Skipping {log_file.path}, file does not exist yet.")
                return

            handler = LogHandler(log_file.path, log_file.id, getattr(log_file, "encoding", "utf-8"))
            self.file_handlers[log_file.id] = handler

            directory = os.path.dirname(log_file.path) or "."
            if directory not in self.dir_handlers:
                dir_handler = DirectoryHandler({log_file.path: handler})
                watch = self.observer.schedule(dir_handler, directory, recursive=False)
                self.dir_handlers[directory] = (dir_handler, watch)
            else:
                dir_handler, _ = self.dir_handlers[directory]
                dir_handler.handlers[log_file.path] = handler

    def stop_watcher(self, log_file):
        self.stop_watcher_by_id(log_file.id, getattr(log_file, "path", None))

    def stop_watcher_by_id(self, log_file_id, path_hint=None):
        with self.lock:
            handler = self.file_handlers.pop(log_file_id, None)
            if not handler:
                return

            filepath = handler.filepath if hasattr(handler, "filepath") else path_hint
            directory = os.path.dirname(filepath) if filepath else None

            if directory and directory in self.dir_handlers:
                dir_handler, watch = self.dir_handlers[directory]
                dir_handler.handlers.pop(filepath, None)

                # If no more files in this directory, unschedule it
                if not dir_handler.handlers:
                    self.observer.unschedule(watch)
                    del self.dir_handlers[directory]

    # ---------- REFRESH ----------
    def refresh(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._refresh_sync()
        else:
            asyncio.create_task(self._refresh_async())

    def _refresh_sync(self):
        existing_ids = set(LogFile.objects.values_list("id", flat=True))

        for logfile_id in list(self.file_handlers.keys()):
            if logfile_id not in existing_ids:
                self.stop_watcher_by_id(logfile_id)

        for lf in LogFile.objects.all():
            if lf.id not in self.file_handlers:
                self.start_watcher(lf)

    async def _refresh_async(self):
        existing_ids = set(await sync_to_async(list)(LogFile.objects.values_list("id", flat=True)))
        for logfile_id in list(self.file_handlers.keys()):
            if logfile_id not in existing_ids:
                self.stop_watcher_by_id(logfile_id)

        log_files = await sync_to_async(list)(LogFile.objects.all())
        for lf in log_files:
            if lf.id not in self.file_handlers:
                self.start_watcher(lf)

    # ---------- STOP ----------
    def stop_all(self):
        with self.lock:
            for logfile_id in list(self.file_handlers.keys()):
                self.stop_watcher_by_id(logfile_id)

        if self._started:
            self.observer.stop()
            self.observer.join()
            self._started = False


# single shared manager instance
log_manager = LogManager()
