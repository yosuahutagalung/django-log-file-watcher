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
        self.handlers = {}        # log_file_id -> handler
        self.lock = threading.Lock()
        self._started = False

    # Public: safe to call from sync or async contexts
    def start_all(self):
        try:
            # If there's a running loop in this thread, schedule an async startup
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop -> safe to call ORM directly (sync context)
            self._start_all_sync()
        else:
            # Running loop -> schedule async version (non-blocking)
            asyncio.create_task(self._start_all_async())

    def _start_all_sync(self):
        """Synchronous startup (safe when called from sync code)."""
        log_files = list(LogFile.objects.all())
        for lf in log_files:
            self.start_watcher(lf)
        with self.lock:
            if not self._started:
                self.observer.start()
                self._started = True

    async def _start_all_async(self):
        """Async startup (safe when called from an async context)."""
        log_files = await sync_to_async(list)(LogFile.objects.all())
        for lf in log_files:
            # start_watcher is sync and thread-safe (uses lock)
            self.start_watcher(lf)
        # observer.start() is sync, but it's fine to call from async task
        with self.lock:
            if not self._started:
                self.observer.start()
                self._started = True

    def start_watcher(self, log_file):
        """Start watcher for a LogFile instance (safe from any context)."""
        with self.lock:
            if log_file.id in self.handlers:
                return

            if not os.path.exists(log_file.path):
                # path doesn't exist yet — skip for now
                print(f"⚠️ Skipping {log_file.path}, file does not exist yet.")
                return

            handler = LogHandler(log_file.path, log_file.id, getattr(log_file, "encoding", "utf-8"))
            # schedule on the directory
            self.observer.schedule(handler, os.path.dirname(log_file.path), recursive=False)
            self.handlers[log_file.id] = handler

    def stop_watcher(self, log_file):
        """Stop watcher given a LogFile instance (safe from any context)."""
        self.stop_watcher_by_id(log_file.id)

    def stop_watcher_by_id(self, log_file_id):
        with self.lock:
            handler = self.handlers.pop(log_file_id, None)
        if handler:
            try:
                self.observer.unschedule(handler)
            except Exception:
                # observer.unschedule may behave differently across watchdog versions;
                # if it errors, ignore to avoid crashing the manager.
                pass

    # Public refresh that is safe in both contexts
    def refresh(self):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # sync
            self._refresh_sync()
        else:
            # async context -> schedule async refresh (non-blocking)
            asyncio.create_task(self._refresh_async())

    def _refresh_sync(self):
        """Synchronous refresh (safe in sync contexts)."""
        existing_ids = set(LogFile.objects.values_list("id", flat=True))

        # Stop watchers for removed logfiles
        for logfile_id in list(self.handlers.keys()):
            if logfile_id not in existing_ids:
                self.stop_watcher_by_id(logfile_id)

        # Start watchers for new logfiles
        for lf in LogFile.objects.all():
            if lf.id not in self.handlers:
                self.start_watcher(lf)

    async def _refresh_async(self):
        """Async refresh (safe in async contexts)."""
        existing_ids = set(await sync_to_async(list)(LogFile.objects.values_list("id", flat=True)))

        # Stop watchers for removed ones
        for logfile_id in list(self.handlers.keys()):
            if logfile_id not in existing_ids:
                self.stop_watcher_by_id(logfile_id)

        # Add new ones
        log_files = await sync_to_async(list)(LogFile.objects.all())
        for lf in log_files:
            if lf.id not in self.handlers:
                self.start_watcher(lf)


# single shared manager instance
log_manager = LogManager()