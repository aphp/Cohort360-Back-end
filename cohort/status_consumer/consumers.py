import json

import jwt
from channels.generic.websocket import AsyncWebsocketConsumer


class StatusConsumer(AsyncWebsocketConsumer):
    clients = {}

    async def connect(self):
        print("connecting")
        token = self.scope['subprotocols'][1]
        cohort_id = self.scope['query_string'].decode('utf-8')
        decoded = jwt.decode(jwt=token,
                             algorithms=['RS256', 'HS256'],
                             options={'verify_signature': False})
        await self.accept()

        client_id = decoded.get('preferred_username')

        self.clients[client_id] = {cohort_id: self}
        await self.send("Welcome")
        await self.send_to_client("finished", client_id, cohort_id)

    async def receive(self, text_data=None, byte_data=None):
        print(f"received message: {text_data}")
        await self.send("Message received")

    async def send_to_client(self, cohort_status, client_id, cohort_id):
        try:
            client_socket = self.clients[client_id][cohort_id]
        except KeyError:
            print(f"Socket not found with {client_id=} {cohort_id=}")
            return
        print(client_socket)

        if client_socket:
            print("sending")
            await client_socket.send(json.dumps({"cohort_status": cohort_status, "cohort_id": cohort_id}))
        else:
            print(f"Client with ID {client_id} not found.")
