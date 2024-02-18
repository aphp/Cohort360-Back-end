import dataclasses
from json import JSONDecodeError
from typing import Literal, Union

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from pydantic import BaseModel

# from admin_cohort.services.auth import auth_service
from admin_cohort.types import JobStatus
from cohort.models import CohortResult, DatedMeasure, FeasibilityStudy

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
        user = self.scope["user"]  # todo: try this
        print(f"********** {user=}")
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
        try:
            # todo: add `auth_method` to the request payload in frontend
            # client_id = auth_service.authenticate_ws_request(token=content['token'],
            #                                                  auth_method=content['auth_method'])

            client_id = self.scope['user'].username
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


def ws_send_to_client(_object: Union[CohortResult, DatedMeasure, FeasibilityStudy], info_type: ws_info_type):
    websocket_infos = WebSocketInfos(status=_object.request_job_status,
                                     client_id=str(_object.owner_id),
                                     uuid=_object.uuid,
                                     type=info_type)
    WebsocketManager.send_to_client(websocket_infos)
