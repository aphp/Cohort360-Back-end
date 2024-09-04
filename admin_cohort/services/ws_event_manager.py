from enum import StrEnum
from json import JSONDecodeError

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from pydantic import BaseModel, Field

from admin_cohort.services.auth import auth_service


class WebSocketMessageType(StrEnum):
    JOB_STATUS = "job_status"
    MAINTENANCE = "maintenance"
    HANDSHAKE = "handshake"


class WebSocketMessage(BaseModel):
    type: WebSocketMessageType = Field(...)


class HandshakeStatus(WebSocketMessage):
    status: str
    details: str = ""


class WebsocketManager(AsyncJsonWebsocketConsumer):

    @sync_to_async
    def authenticate_ws_request(self, token, auth_method, headers):
        return auth_service.authenticate_ws_request(token, auth_method, headers)

    async def connect(self):
        await self.accept()

    @staticmethod
    def send_to_client(client_or_group_id: str, message: WebSocketMessage):
        channel_layer = get_channel_layer()
        payload = {'type': 'object_status_handler', 'payload': message.model_dump()}
        async_to_sync(channel_layer.group_send)(client_or_group_id, payload)

    async def object_status_handler(self, event):
        """Send any message to the clients"""
        await self.send_json(event["payload"])

    async def receive_json(self, content, **kwargs):
        try:
            client = await self.authenticate_ws_request(token=content['token'],
                                                        auth_method=content['auth_method'],
                                                        headers=content.get('headers') or {})
            client_id = client.username
            await self.send_json(HandshakeStatus(type=WebSocketMessageType.HANDSHAKE, status='accepted').model_dump())
        except KeyError:
            await self.send_json(HandshakeStatus(
                type=WebSocketMessageType.HANDSHAKE,
                status='pending',
                details='Could not understand the JSON object, "token" key missing').model_dump())
            return
        except Exception:
            await self.send_json(
                HandshakeStatus(type=WebSocketMessageType.HANDSHAKE, status='forbidden', details='Bad token').model_dump())
            await self.close()
            return
        await self.channel_layer.group_add(f"{client_id}", self.channel_name)
        await self.channel_layer.group_add("__all__", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            await super().receive(text_data, bytes_data)
        except JSONDecodeError:
            return
