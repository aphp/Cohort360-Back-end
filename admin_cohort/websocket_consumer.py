import asyncio
from typing import Callable

import websockets


class WebSocketStatusConsumer:
    def __init__(self, check_client_fn: Callable):
        self.check_client_fn = check_client_fn
        self.clients = {}

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "").lstrip("/")
        if path.startswith("job/") and "/" in path:
            job_id = path.split("/")[1]
            if not await self.check_client_fn(job_id):
                raise websockets.ConnectionClosed(None, None)
            await self.handle_client(websockets.WebSocketCommonProtocol(scope, receive, send), job_id)

    async def authenticate_client(self, receive, expected_token):
        # todo: check if the client is really the owner of the cohort (dm_uuid.owner)
        websocket = await receive()
        client_token = await websocket.receive()
        if client_token == expected_token:
            return websocket
        return None

    async def handle_client(self, websocket, path):
        print(f"Client connected with path: {path}")

        # Send a welcome message to the client
        await websocket.send(f"Welcome to the server, you are connected to path: {path}")
        await asyncio.get_event_loop().create_task(self.simulate_status_updates(path))

        try:
            while True:
                # We are not waiting for anything from the client
                # todo: close the connection when there is no more status to be updated
                pass
        except websockets.exceptions.ConnectionClosedError:
            print(f"Client {path} disconnected.")

    async def simulate_status_updates(self, path):
        """Testing method to simulate status updates"""
        await asyncio.sleep(2)  # Simulate a delay
        await self.send_status_update(path, "FINISHED")

    async def send_status_update(self, path, status):
        await self.clients[path].send(status)
