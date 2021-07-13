from typing import List
import asyncio
import enum
import json

from .rabbitmq_connector import send_message


class Statuses(enum.Enum):
    staged = "Staged"
    processing = "Processing"
    failed = "Failed"
    successful = "Successful"


class Notificator:
    def __init__(self, statuses: List[str], routing_key: str):
        self.statuses = {status: Statuses.staged for status in statuses}
        self.routing_key = routing_key

        try:
            self.loop = asyncio.get_event_loop()
        except Exception:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def update_status(self, key, status, task_id):
        self.statuses[key] = status

        message = {
            'id': task_id,
            'type': 'status_update'
        }

        for stage, status in self.statuses.items():
            message[stage] = status.value

        message = json.dumps(message)

        asyncio.create_task(send_message(message, self.loop, self.routing_key))
