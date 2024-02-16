import dataclasses
from json import JSONDecodeError
from typing import Literal

import jwt
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from pydantic import BaseModel

from admin_cohort.types import JobStatus


@dataclasses.dataclass
class WebSocketInfos:
    status: JobStatus
    client_id: str
    uuid: str
    type: Literal['count', 'create', 'feasibility']


class WebSocketObject(BaseModel):
    type: str


class WebSocketStatus(WebSocketObject):
    uuid: str
    status: str


class HandshakeStatus(WebSocketObject):
    status: str
    details: str = ""


class WebsocketManager(AsyncJsonWebsocketConsumer):

    def get_client_id_from_token(self, jwt_token: str) -> str:
        decoded = jwt.decode(jwt=jwt_token,
                             algorithms=['RS256', 'HS256'],
                             options={'verify_signature': False})
        return decoded.get('preferred_username') or decoded.get('username')

    async def connect(self):
        await self.accept()

    @staticmethod
    def send_to_client(ws_infos: WebSocketInfos):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"{ws_infos.client_id}",
            {
                'type': 'cohort_status',  # finds handler method cohort_status
                'cohort_status': ws_infos.status,
                'uuid': ws_infos.uuid,
            }
        )

    async def cohort_status(self, event):
        """Send an update for the count, create and feasibility status"""
        ws_status = WebSocketStatus(type='status', uuid=event['uuid'], status=event['cohort_status'])
        await self.send_json(ws_status.model_dump())

    async def receive_json(self, content, **kwargs):
        try:
            token = content['token']
            client_id = self.get_client_id_from_token(token)

            await self.send_json(HandshakeStatus(type='handshake', status='accepted').model_dump())

        except KeyError:
            await self.send_json(
                HandshakeStatus(type='handshake', status='pending',
                                details='Could not understand the JSON object, "token" key missing').model_dump())
            return

        except Exception:
            await self.send_json(
                HandshakeStatus(type='handshake', status='forbidden', details='Bad token').model_dump())
            await self.close()
            return
        await self.channel_layer.group_add(f"{client_id}", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            await super().receive(text_data, bytes_data)
        except JSONDecodeError:
            return
