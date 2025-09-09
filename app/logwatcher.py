from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from .models import LogFile

class LogHandler(FileSystemEventHandler):
    def __init__(self, filepath, log_id):
        self.filepath = filepath
        self.log_id = log_id
        self._pos = 0
        self.channel_layer = get_channel_layer()

    def on_modified(self, event):
        if event.src_path.endswith(self.filepath):
            with open(self.filepath, "r") as f:
                f.seek(self._pos)
                for line in f:
                    async_to_sync(self.channel_layer.group_send)(
                        f"logs_{self.log_id}",
                        {"type": "log_message", "line": line.strip()},
                    )
                self._pos = f.tell()


class LogManager:
    def __init__(self):
        self.observer = Observer()
        self.handlers = {}

    def start_all(self):
        for log_file in LogFile.objects.all():
            self.start_watcher(log_file)
        self.observer.start()

    def start_watcher(self, log_file):
        if log_file.id in self.handlers:
            return

        handler = LogHandler(log_file.path, log_file.id)
        self.observer.schedule(handler, log_file.path, recursive=False)
        self.handlers[log_file.id] = handler

    def stop_watcher(self, log_file):
        handler = self.handlers.pop(log_file.id, None)
        if handler:
            self.observer.unschedule(handler)

    def refresh(self):
        # Remove missing ones
        for log_file_id in list(self.handlers.keys()):
            if not LogFile.objects.filter(id=log_file_id).exists():
                self.stop_watcher(LogFile(id=log_file_id))

        # Add new ones
        for log_file in LogFile.objects.all():
            if log_file.id not in self.handlers:
                self.start_watcher(log_file)

log_manager = LogManager()