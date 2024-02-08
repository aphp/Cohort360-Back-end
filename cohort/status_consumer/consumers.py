import dataclasses
from typing import Literal

import jwt
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer


@dataclasses.dataclass
class WebsocketParams:
    action_type: Literal['count', 'create', 'feasibility']
    uuid: str


class StatusConsumer(AsyncWebsocketConsumer):
    clients = {}

    def get_client_id_from_token(self, jwt_token: str) -> str:
        decoded = jwt.decode(jwt=jwt_token,
                             algorithms=['RS256', 'HS256'],
                             options={'verify_signature': False})
        return decoded.get('preferred_username')

    def parse_params(self) -> WebsocketParams | None:
        try:
            uuid = self.scope['path'].split('/')[-1]
            action_type = "count"  # todo: get it scope
            return WebsocketParams(uuid, action_type)
        except Exception:  # Bad format for params
            self.close()
            return None

    async def connect(self):
        try:
            client_id = self.get_client_id_from_token("test_token")
            await self.accept()
        except Exception:  # todo: raise User does not exist
            await self.close()
            return

        params = self.parse_params()
        await self.channel_layer.group_add(f"{params.action_type}_{client_id}_{params.uuid}", self.channel_name)

    @staticmethod
    def send_to_client(cohort_status, client_id, cohort_id, prefix):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"{prefix}_{client_id}_{cohort_id}",
            {
                'type': 'cohort_status',
                'cohort_status': cohort_status,
                'cohort_id': cohort_id,
            }
        )

    async def cohort_status(self, event):
        cohort_status = event['cohort_status']
        cohort_id = event['cohort_id']

        # Send the cohort_status message to the WebSocket
        await self.send(text_data=f"Cohort {cohort_id} status: {cohort_status}")
