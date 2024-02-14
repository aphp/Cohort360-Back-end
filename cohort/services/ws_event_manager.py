import json

import jwt
from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer

from admin_cohort.models import User


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
        except User.DoesNotExist:
            await self.close()
            return

        await self.channel_layer.group_add(f"{client_id}", self.channel_name)

    @staticmethod
    def send_to_client(cohort_status, client_id, cohort_id, prefix):
        if client_id not in WebsocketManager.accepted_clients:
            return
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"{client_id}",
            {
                'type': prefix,
                'cohort_status': cohort_status,
                'cohort_id': cohort_id,
            }
        )

    async def cohort_status(self, event):
        cohort_status = event['cohort_status']
        cohort_id = event['cohort_id']

        await self.send(json.dumps({'type': 'status', 'uuid': cohort_id, 'status': cohort_status}))
