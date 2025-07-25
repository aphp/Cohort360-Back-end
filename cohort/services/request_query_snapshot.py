import json
import logging
from typing import List, Optional

from django.conf import settings

from admin_cohort.models import User
from admin_cohort.tools.cache import invalidate_cache
from cohort.services.emails import send_email_notif_about_shared_request
from cohort.models import RequestQuerySnapshot, Folder, Request

_logger_err = logging.getLogger('django.request')


class RequestQuerySnapshotService:

    @staticmethod
    def process_creation_data(data: dict) -> None:
        previous_snapshot_id = data.get("previous_snapshot")
        request_id = data.get("request")
        if previous_snapshot_id:
            previous_snapshot = RequestQuerySnapshot.objects.get(pk=previous_snapshot_id)
            if request_id and request_id != previous_snapshot.request_id:
                raise ValueError("The provided request is different from the previous_snapshot's request")
            data["request"] = previous_snapshot.request_id
        elif request_id:
            request = Request.objects.get(pk=request_id)
            if request.query_snapshots.exists():
                raise ValueError("Must provide a `previous_snapshot` if the request already has snapshots")
        else:
            raise ValueError("Neither `previous_snapshot` nor `request` were provided")

        serialized_query = data.get("serialized_query")
        data["perimeters_ids"] = RequestQuerySnapshotService.retrieve_perimeters(json_query=serialized_query)
        request = Request.objects.get(pk=data.get("request"))
        data["version"] = request.query_snapshots.count() + 1

    @staticmethod
    def check_shared_folders(recipients: List[User]) -> tuple[List[Folder], dict[str, Folder]]:
        existing_shared_folders = Folder.objects.filter(name=settings.SHARED_FOLDER_NAME,
                                                        owner__in=recipients)
        recipients_having_shared_folder = []
        folders_by_owner = {}
        for folder in existing_shared_folders:
            recipients_having_shared_folder.append(folder.owner)
            folders_by_owner[folder.owner.pk] = folder

        folders_to_create = []
        for recipient in recipients:
            if recipient not in recipients_having_shared_folder:
                folder = Folder(name=settings.SHARED_FOLDER_NAME, owner=recipient)
                folders_to_create.append(folder)
                folders_by_owner[recipient.pk] = folder
        return folders_to_create, folders_by_owner

    @staticmethod
    def create_requests(snapshot: RequestQuerySnapshot, request_name: str, folders_by_owner: dict) -> dict[str, Request]:
        requests_by_owner = {}
        for owner_id, folder in folders_by_owner.items():
            request = Request(**{**{field.name: getattr(snapshot.request, field.name)
                                    for field in Request._meta.fields if field.name != Request._meta.pk.name
                                    },
                                 'owner_id': owner_id,
                                 'favorite': False,
                                 'name': request_name,
                                 'shared_by': snapshot.owner,
                                 'parent_folder': folder
                                 })
            requests_by_owner[owner_id] = request
        return requests_by_owner

    @staticmethod
    def create_snapshots(snapshot: RequestQuerySnapshot, requests_by_owner: dict) -> List[RequestQuerySnapshot]:
        snapshots = []
        for owner_id, request in requests_by_owner.items():
            snapshots.append(RequestQuerySnapshot(**{**{field.name: getattr(snapshot, field.name)
                                                        for field in RequestQuerySnapshot._meta.fields
                                                        if field.name != RequestQuerySnapshot._meta.pk.name
                                                        },
                                                     'shared_by': snapshot.owner,
                                                     'owner_id': owner_id,
                                                     'previous_snapshot': None,
                                                     'request': request,
                                                     'version': 1,
                                                     }))
        return snapshots

    @staticmethod
    def share_snapshot(snapshot: RequestQuerySnapshot, request_name: str, recipients_ids: str, notify_by_email: bool) -> None:
        if not recipients_ids:
            raise ValueError("No 'recipients' provided")

        recipients_ids = recipients_ids.split(",")
        recipients = User.objects.filter(pk__in=recipients_ids)
        missing_recipients_ids = [uid for uid in recipients_ids if uid not in recipients.values_list("pk", flat=True)]

        if missing_recipients_ids:
            raise ValueError(f"No users found with the following IDs: {','.join(missing_recipients_ids)}")

        request_name = request_name or snapshot.request.name

        folders_to_create, folders_by_owner = RequestQuerySnapshotService.check_shared_folders(recipients=recipients)
        requests_by_owner = RequestQuerySnapshotService.create_requests(snapshot=snapshot,
                                                                        request_name=request_name,
                                                                        folders_by_owner=folders_by_owner)
        snapshots = RequestQuerySnapshotService.create_snapshots(snapshot=snapshot,
                                                                 requests_by_owner=requests_by_owner)

        Folder.objects.bulk_create(folders_to_create)
        Request.objects.bulk_create(requests_by_owner.values())
        RequestQuerySnapshot.objects.bulk_create(snapshots)

        for model in (Folder, Request, RequestQuerySnapshot):
            invalidate_cache(model_name=model.__name__)

        if notify_by_email:
            for recipient in recipients:
                send_email_notif_about_shared_request(request_name=request_name,
                                                      owner=snapshot.owner,
                                                      recipient=recipient)

    @staticmethod
    def retrieve_perimeters(json_query: str) -> List[str]:
        try:
            query = json.loads(json_query)
            perimeters_ids = query["sourcePopulation"]["caresiteCohortList"]
            assert all(i.isnumeric() for i in perimeters_ids), "Perimeters IDs must be integers"
            return perimeters_ids
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            msg = f"Error extracting perimeters ids from JSON query - {e}"
            _logger_err.exception(msg=msg)
            raise ValueError(msg)

    @staticmethod
    def update_query_perimeter(json_query: str, matching: dict[str, Optional[str]], raise_on_error=False) -> str:
        try:
            query = json.loads(json_query)
            perimeters_ids = query["sourcePopulation"]["caresiteCohortList"]
            updated_perimeters_ids = sorted({matching.get(pid, pid) or pid for pid in perimeters_ids})
            query["sourcePopulation"]["caresiteCohortList"] = updated_perimeters_ids
            return json.dumps(query)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            msg = f"Error updating perimeters ids from JSON query - {e}"
            _logger_err.exception(msg=msg)
            if raise_on_error:
                raise ValueError(msg)
            return json_query


rqs_service = RequestQuerySnapshotService()
