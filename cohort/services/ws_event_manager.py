import dataclasses
from json import JSONDecodeError
from typing import Literal, Union

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from pydantic import BaseModel

from admin_cohort.types import JobStatus

ws_info_type = Literal['count', 'create', 'feasibility']


@dataclasses.dataclass
class WebSocketInfos:
    status: Union[JobStatus, str]
    client_id: str
    uuid: str
    type: ws_info_type


class WebSocketObject(BaseModel):
    type: str


class WebSocketStatus(WebSocketObject):
    uuid: str
    status: str


class HandshakeStatus(WebSocketObject):
    status: str
    details: str = ""


class WebsocketManager(AsyncJsonWebsocketConsumer):

    async def connect(self):
        try:
            subprotocol = self.scope.get('subprotocols')[0]
            client_id = self.scope['user'].username
        except (IndexError, KeyError):
            await self.close()
        else:
            await self.accept(subprotocol=subprotocol)
            await self.channel_layer.group_add(client_id, self.channel_name)

    @staticmethod
    def send_to_client(ws_infos: WebSocketInfos):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(ws_infos.client_id,
                                                {'type': 'object_status_handler',  # finds handler method `object_status_handler`
                                                 'object_status': ws_infos.status,
                                                 'uuid': ws_infos.uuid
                                                 })

    async def object_status_handler(self, event):
        """Send an update for the count, create and feasibility status"""
        ws_status = WebSocketStatus(type='status', uuid=event['uuid'], status=event['object_status'])
        await self.send_json(ws_status.model_dump())

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            await super().receive(text_data, bytes_data)
        except JSONDecodeError:
            return


def ws_send_to_client(_object, info_type: ws_info_type):
    websocket_infos = WebSocketInfos(status=_object.request_job_status,
                                     client_id=str(_object.owner_id),
                                     uuid=_object.uuid,
                                     type=info_type)
    WebsocketManager.send_to_client(websocket_infos)
