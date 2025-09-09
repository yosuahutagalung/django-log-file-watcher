from channels.generic.websocket import AsyncWebsocketConsumer
import json

class LogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.log_id = self.scope["url_route"]["kwargs"]["log_id"]
        self.group_name = f"logs_{self.log_id}"

        # Join app-specific group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def log_message(self, event):
        await self.send(text_data=json.dumps({
            "line": event["line"],
            "app": self.log_id,
        }))
