from json import JSONDecodeError
from typing import Literal, Union

from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from pydantic import BaseModel

from admin_cohort.services.auth import auth_service
from admin_cohort.types import JobStatus

ws_info_type = Literal['status']
ws_info_job_name = Literal['count', 'create']


class WebSocketInfos(BaseModel):
    status: Union[JobStatus, str]
    client_id: str
    uuid: str
    type: ws_info_type
    job_name: ws_info_job_name
    extra_info: dict


class WebSocketObject(BaseModel):
    type: str


class HandshakeStatus(WebSocketObject):
    status: str
    details: str = ""


class WebsocketManager(AsyncJsonWebsocketConsumer):

    @sync_to_async
    def authenticate_ws_request(self, token, auth_method, headers):
        return auth_service.authenticate_ws_request(token, auth_method, headers)

    async def connect(self):
        await self.accept()

    @staticmethod
    def send_to_client(ws_infos: WebSocketInfos):
        channel_layer = get_channel_layer()
        payload = {'type': 'object_status_handler', 'payload': ws_infos.model_dump()}
        async_to_sync(channel_layer.group_send)(f"{ws_infos.client_id}", payload)

    async def object_status_handler(self, event):
        """Send an update for the count, create of type WebSocketInfos"""
        await self.send_json(event["payload"])

    async def receive_json(self, content, **kwargs):
        try:
            client = await self.authenticate_ws_request(token=content['token'],
                                                        auth_method=content['auth_method'],
                                                        headers=content.get('headers') or {})
            client_id = client.username
            await self.send_json(HandshakeStatus(type='handshake', status='accepted').model_dump())
        except KeyError:
            await self.send_json(HandshakeStatus(type='handshake',
                                                 status='pending',
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


def ws_send_to_client(instance, job_name: ws_info_job_name, extra_info: dict):
    websocket_infos = WebSocketInfos(status=instance.request_job_status,
                                     client_id=str(instance.owner_id),
                                     uuid=str(instance.uuid),
                                     type='status',
                                     job_name=job_name,
                                     extra_info=extra_info)
    WebsocketManager.send_to_client(websocket_infos)
