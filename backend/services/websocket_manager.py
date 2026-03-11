import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
from loguru import logger

class OverrideMessage:
    def __init__(self, entity_id: str, new_directive: str):
        self.entity_id = entity_id
        self.new_directive = new_directive

class OverrideQueue:
    """Stores the latest overrides for a specific spark run."""
    def __init__(self):
        self._queue: list[OverrideMessage] = []
        
    def push(self, msg: OverrideMessage):
        self._queue.append(msg)
        
    def has_pending(self) -> bool:
        return len(self._queue) > 0
        
    def pop_all(self) -> list[OverrideMessage]:
        msgs = self._queue[:]
        self._queue.clear()
        return msgs

class ConnectionManager:
    def __init__(self):
        # We only support a single local connection for the MVP
        self.active_connection: Optional[WebSocket] = None
        # spark_id -> OverrideQueue
        self.override_queues: Dict[str, OverrideQueue] = {}
        # spark_id -> asyncio.Task
        self.active_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connection = websocket
        logger.info("WebSocket connection established")

    def disconnect(self):
        self.active_connection = None
        logger.info("WebSocket connection closed")

    async def broadcast(self, event_type: str, payload: dict):
        if self.active_connection is None:
            return
            
        message = {
            "type": event_type,
            "payload": payload
        }
        try:
            await self.active_connection.send_json(message)
        except Exception as e:
            logger.error(f"Failed to broadcast WS message: {e}")

    def get_ws_override_queue(self, spark_id: str) -> OverrideQueue:
        if spark_id not in self.override_queues:
            self.override_queues[spark_id] = OverrideQueue()
        return self.override_queues[spark_id]
        
    def register_task(self, spark_id: str, task: asyncio.Task):
        self.active_tasks[spark_id] = task
        
    def cancel_task(self, spark_id: str):
        if spark_id in self.active_tasks:
            logger.warning(f"Cancelling Task {spark_id} due to CUT command.")
            self.active_tasks[spark_id].cancel()

manager = ConnectionManager()
