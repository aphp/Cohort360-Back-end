import dataclasses
import logging
from json import JSONDecodeError
from typing import Literal, Union

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from pydantic import BaseModel

from admin_cohort.services.auth import auth_service
from admin_cohort.types import JobStatus

_logger = logging.getLogger('info')

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

    @sync_to_async
    def authenticate_ws_request(self, token, auth_method):
        return auth_service.authenticate_ws_request(token, auth_method)

    async def connect(self):
        await self.accept()

    @staticmethod
    def send_to_client(ws_infos: WebSocketInfos):
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"{ws_infos.client_id}",
            {
                'type': 'object_status_handler',  # finds handler method `object_status_handler`
                'object_status': ws_infos.status,
                'uuid': ws_infos.uuid,
            }
        )

    async def object_status_handler(self, event):
        """Send an update for the count, create and feasibility status"""
        ws_status = WebSocketStatus(type='status', uuid=event['uuid'], status=event['object_status'])
        await self.send_json(ws_status.model_dump())

    async def receive_json(self, content, **kwargs):
        _logger.info(f"[WS] - Received json message: {content}")
        try:
            client = await self.authenticate_ws_request(token=content['token'],
                                                        auth_method=content['auth_method'])
            client_id = client.username
            _logger.info(f"[WS] - Successfully authenticated client: {client_id=}")
            await self.send_json(HandshakeStatus(type='handshake', status='accepted').model_dump())
        except KeyError:
            _logger.error(f"[WS] - KeyError on received json message: {content}")
            await self.send_json(HandshakeStatus(type='handshake',
                                                 status='pending',
                                                 details='Could not understand the JSON object, "token" key missing').model_dump())
            return
        except Exception as e:
            _logger.error(f"[WS] - Error on received json message: {content=}, Error: {e}")
            await self.send_json(HandshakeStatus(type='handshake', status='forbidden', details='Bad token').model_dump())
            await self.close()
            return
        await self.channel_layer.group_add(f"{client_id}", self.channel_name)

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
