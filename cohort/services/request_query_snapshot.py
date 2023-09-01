from typing import List

from admin_cohort.models import User
from admin_cohort.settings import SHARED_FOLDER_NAME
from admin_cohort.tools.cache import invalidate_cache
from cohort.models import RequestQuerySnapshot, Folder, Request
from cohort.tools import send_email_notif_about_request_sharing


class RequestQuerySnapshotService:

    @staticmethod
    def check_shared_folders(recipients: List[User]) -> tuple[List[Folder], dict[str, Folder]]:
        existing_shared_folders = Folder.objects.filter(name=SHARED_FOLDER_NAME,
                                                        owner__in=recipients)
        recipients_having_shared_folder = []
        folders_by_owner = {}
        for folder in existing_shared_folders:
            recipients_having_shared_folder.append(folder.owner)
            folders_by_owner[folder.owner.pk] = folder

        folders_to_create = []
        for recipient in recipients:
            if recipient not in recipients_having_shared_folder:
                folder = Folder(name=SHARED_FOLDER_NAME, owner=recipient)
                folders_to_create.append(folder)
                folders_by_owner[recipient.pk] = folder
        return folders_to_create, folders_by_owner

    @staticmethod
    def create_requests(snapshot: RequestQuerySnapshot, request_name: str, folders_by_owner: dict) -> dict[str, Request]:
        requests_by_owner = {}
        for owner_id, folder in folders_by_owner.items():
            request = Request(**{**dict([(field.name, getattr(snapshot.request, field.name))
                                         for field in Request._meta.fields
                                         if field.name != Request._meta.pk.name]),
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
            snapshots.append(RequestQuerySnapshot(**{**dict([(field.name, getattr(snapshot, field.name))
                                                             for field in RequestQuerySnapshot._meta.fields
                                                             if field.name != RequestQuerySnapshot._meta.pk.name]),
                                                     'shared_by': snapshot.owner,
                                                     'owner_id': owner_id,
                                                     'previous_snapshot': None,
                                                     'is_active_branch': True,
                                                     'request': request,
                                                     'version': 1,
                                                     }))
        return snapshots

    @staticmethod
    def share_snapshot(snapshot: RequestQuerySnapshot, request_name: str, recipients_ids: str, notify_by_email: bool):
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
        shared_snapshots = RequestQuerySnapshot.objects.bulk_create(snapshots)

        for model in (Folder, Request, RequestQuerySnapshot):
            invalidate_cache(model_name=model.__name__)

        if notify_by_email:
            for recipient in recipients:
                send_email_notif_about_request_sharing(request_name=request_name,
                                                       owner=snapshot.owner,
                                                       recipient=recipient)
        return shared_snapshots


rqs_service = RequestQuerySnapshotService()
