import dataclasses
import json
from typing import Literal

import jwt
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

from admin_cohort.models import User
from admin_cohort.types import JobStatus


@dataclasses.dataclass
class WebSocketInfos:
    status: JobStatus
    client_id: str
    uuid: str
    type: Literal['count', 'create', 'feasibility']


class WebsocketManager(AsyncWebsocketConsumer):
    accepted_clients = set()

    def get_client_id_from_token(self, jwt_token: str) -> str:
        decoded = jwt.decode(jwt=jwt_token,
                             algorithms=['RS256', 'HS256'],
                             options={'verify_signature': False})
        return decoded.get('preferred_username')

    async def connect(self):
        token = await self.receive()
        try:
            client_id = self.get_client_id_from_token(token)
            await self.accept()
            WebsocketManager.accepted_clients.add(client_id)
        except User.DoesNotExist:
            await self.close()
            return

        await self.channel_layer.group_add(f"{client_id}", self.channel_name)

    @staticmethod
    def send_to_client(ws_infos: WebSocketInfos):
        if ws_infos.client_id not in WebsocketManager.accepted_clients:
            return
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"{ws_infos.client_id}",
            {
                'type': ws_infos.type,
                'cohort_status': ws_infos.status,
                'uuid': ws_infos.uuid,
            }
        )

    async def cohort_status(self, event):
        """Send an update for the count, create and feasibility status"""
        cohort_status = event['cohort_status']
        cohort_id = event['cohort_id']

        await self.send(json.dumps({'type': 'status', 'uuid': cohort_id, 'status': cohort_status}))
