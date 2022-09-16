import random
from datetime import timedelta
from typing import List
from unittest import mock
from unittest.mock import MagicMock

from django.utils import timezone
from rest_framework import status
from rest_framework.test import force_authenticate

from admin_cohort.models import User
from admin_cohort.settings import SHARED_FOLDER_NAME
from admin_cohort.tools import prettify_json
from admin_cohort.types import JobStatus
from cohort.FhirAPi import FhirValidateResponse, FhirCountResponse, \
    FhirCohortResponse
from admin_cohort.tests_tools import ViewSetTests, new_random_user, \
    random_str, ListCase, RetrieveCase, CreateCase, CaseRetrieveFilter, \
    DeleteCase, PatchCase, RequestCase
from cohort.models import Request, RequestQuerySnapshot, DatedMeasure, \
    CohortResult, Folder, REQUEST_DATA_TYPE_CHOICES, \
    PATIENT_REQUEST_TYPE, DATED_MEASURE_MODE_CHOICES, SNAPSHOT_DM_MODE, \
    GLOBAL_DM_MODE
from cohort.tasks import get_count_task, create_cohort_task
from cohort.views import RequestViewSet, RequestQuerySnapshotViewSet, \
    DatedMeasureViewSet, CohortResultViewSet, FolderViewSet, \
    NestedRequestViewSet, NestedRqsViewSet, NestedDatedMeasureViewSet, \
    NestedCohortResultViewSet

EXPLORATIONS_URL = "/cohort"
FOLDERS_URL = f"{EXPLORATIONS_URL}/folders"
REQUESTS_URL = f"{EXPLORATIONS_URL}/requests"
RQS_URL = f"{EXPLORATIONS_URL}/request-query-snapshots"
DATED_MEASURES_URL = f"{EXPLORATIONS_URL}/dated-measures"
COHORTS_URL = f"{EXPLORATIONS_URL}/cohorts"

REQUEST_STATUS_CHOICES = [(e.name.lower(), e.name.lower()) for e in JobStatus]


# TODO : test for post save0 get saved, get last_modified,
# TODO : make test for create/get Request's Rqs, Rqs' dated_measure,
#  Rqs' cohortresult
# TODO : prevent add rqs with previous not on active branch

class FolderCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str = "", **kwargs):
        self.name = name
        super(FolderCaseRetrieveFilter, self).__init__(**kwargs)


class RequestCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str = "", **kwargs):
        self.name = name
        super(RequestCaseRetrieveFilter, self).__init__(**kwargs)


class RQSCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, serialized_query: str = "", **kwargs):
        self.serialized_query = serialized_query
        super(RQSCaseRetrieveFilter, self).__init__(**kwargs)


# FOLDERS

class CohortAppTests(ViewSetTests):
    def setUp(self):
        super(CohortAppTests, self).setUp()
        self.user1 = new_random_user(firstname="Squall", lastname="Leonheart",
                                     email='s.l@aphp.fr')
        self.user2 = new_random_user(firstname="Seifer", lastname="Almasy",
                                     email='s.a@aphp.fr')
        self.users = [self.user1, self.user2]


class FoldersTests(CohortAppTests):
    unupdatable_fields = ["created_at", "modified_at", "deleted"]
    unsettable_default_fields = dict()
    unsettable_fields = ["owner", "uuid", "created_at", "modified_at",
                         "deleted"]
    manual_dupplicated_fields = []

    objects_url = "cohort/folders/"
    retrieve_view = FolderViewSet.as_view({'get': 'retrieve'})
    list_view = FolderViewSet.as_view({'get': 'list'})
    create_view = FolderViewSet.as_view({'post': 'create'})
    delete_view = FolderViewSet.as_view({'delete': 'destroy'})
    update_view = FolderViewSet.as_view({'patch': 'partial_update'})
    model = Folder
    model_objects = Folder.objects
    model_fields = Folder._meta.fields


class FoldersGetTests(FoldersTests):
    def setUp(self):
        super(FoldersGetTests, self).setUp()
        nb_base = 20
        self.name_pattern = "aAa"

        self.folders: List[Folder] = Folder.objects.bulk_create([
            Folder(
                name=random_str(10, random.random() > .5 and self.name_pattern),
                owner=random.choice([self.user1, self.user2]),
            ) for i in range(0, nb_base)
        ])
        for f in self.folders[:nb_base]:
            self.folders += Folder.objects.bulk_create([
                Folder(
                    name=random_str(10,
                                    random.random() > .5 and self.name_pattern),
                    owner=f.owner,
                    parent_folder=f
                )
            ])

    def test_list(self):
        # As a user, I can list the folders I own
        case = ListCase(
            to_find=[f for f in self.folders if f.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single folder I own
        to_find = [f for f in self.folders if f.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single folder I do not own
        to_find = [f for f in self.folders if f.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)

    def test_list_with_filters(self):
        # As a user, I can list the folders I own
        basic_case = ListCase(user=self.user1, success=True,
                              status=status.HTTP_200_OK)
        user1_folders = [f for f in self.folders if f.owner == self.user1]
        parent_folder = next(f for f in user1_folders
                             if f.parent_folder is not None).parent_folder
        cases = [
            basic_case.clone(
                params=dict(parent_folder=parent_folder.pk),
                to_find=list(parent_folder.children_folders.all()),
            ),
            basic_case.clone(
                params=dict(name=self.name_pattern),
                to_find=[f for f in user1_folders
                         if self.name_pattern.lower() in f.name],
            )
        ]
        [self.check_get_paged_list_case(case) for case in cases]


class FoldersCreateTests(FoldersTests):
    def setUp(self):
        super(FoldersCreateTests, self).setUp()
        self.test_name = "test"
        self.main_folder_name = "Main"
        self.user1_folder = Folder.objects.create(
            name=self.main_folder_name, owner=self.user1)
        self.user2_folder = Folder.objects.create(
            name=self.main_folder_name, owner=self.user2)

        self.basic_data = dict(
            parent_folder=self.user1_folder.pk,
            name=self.test_name,
        )
        self.basic_case = CreateCase(
            success=True,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            data=self.basic_data,
            retrieve_filter=FolderCaseRetrieveFilter(name=self.test_name,
                                                     owner=self.user1)
        )

    def test_create(self):
        # As a user, I can create a folder
        self.check_create_case(self.basic_case)

    def test_create_with_unread_fields(self):
        # As a user, I can create a request
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1)},
        ))

    def test_error_create_missing_field(self):
        # As a user, I cannot create a folder if some fields are missing
        cases = (self.basic_case.clone(
            data={**self.basic_data, k: None},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ) for k in ['name'])
        [self.check_create_case(case) for case in cases]

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a folder
        self.check_create_case(self.basic_case.clone(
            data=dict(parent_folder_id=self.user1_folder.pk,
                      owner=self.user2.pk,
                      name=self.test_name),
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            retrieve_filter=FolderCaseRetrieveFilter(
                name=self.test_name,
                owner=self.user2
            ),
        ))

    def test_error_create_with_wrong_parent(self):
        # As a user, I cannot create a folder
        self.check_create_case(self.basic_case.clone(
            data=dict(parent_folder_id=self.user2_folder.pk,
                      owner_id=self.user1.pk,
                      name=self.test_name),
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            retrieve_filter=FolderCaseRetrieveFilter(
                name=self.test_name,
                owner=self.user1
            ),
        ))

    def test_error_create_with_same_user_name_and_parent(self):
        # As a user, I cannot create a folder with a name already taken
        self.check_create_case(self.basic_case.clone(
            data=dict(owner_id=self.user1.pk,
                      name=self.main_folder_name),
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            retrieve_filter=FolderCaseRetrieveFilter(
                name=self.test_name,
                owner=self.user1
            ),
        ))


class FoldersDeleteTests(FoldersTests):
    def setUp(self):
        super(FoldersDeleteTests, self).setUp()
        self.basic_case = DeleteCase(
            data_to_delete=dict(),
            status=status.HTTP_204_NO_CONTENT,
            success=True,
            user=self.user1,
        )

    def test_delete_as_owner(self):
        # As a user, I can delete a folder I created
        self.check_delete_case(self.basic_case.clone(
            data_to_delete=dict(owner=self.user1, name="test")
        ))

    def test_error_delete_as_not_owner(self):
        # As a user, I cannot delete another user's folder
        self.check_delete_case(self.basic_case.clone(
            data_to_delete=dict(owner=self.user1, name="test"),
            user=self.user2,
            success=False,
            status=status.HTTP_404_NOT_FOUND,
        ))


class FoldersUpdateTests(FoldersTests):
    def setUp(self):
        super(FoldersUpdateTests, self).setUp()
        self.user1_folder = Folder.objects.create(owner=self.user1, name="Main")
        self.basic_case = PatchCase(
            data_to_update=dict(),
            initial_data=dict(),
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
        )

    def test_update_as_owner(self):
        # As a user, I can patch a folder I own
        self.check_patch_case(self.basic_case.clone(
            initial_data=dict(owner=self.user1, name="test"),
            data_to_update=dict(
                name="new_name",
                parent_folder=self.user1_folder.pk,
                # read_only
                created_at=timezone.now() + timedelta(hours=1),
                modified_at=timezone.now() + timedelta(hours=1),
                deleted=timezone.now() + timedelta(hours=1),
            )
        ))

    def test_error_update_as_not_owner(self):
        # As a user, I cannot patch a folder I do not own
        self.check_patch_case(self.basic_case.clone(
            initial_data=dict(owner=self.user2, name="test"),
            data_to_update=dict(name="new_name"),
            success=False,
            status=status.HTTP_404_NOT_FOUND,
        ))

    def test_error_update_forbidden_fields(self):
        # As a user, I cannot patch a folder I with forbidden values
        self.check_patch_case(self.basic_case.clone(
            initial_data=dict(owner=self.user1, name="test"),
            data_to_update=dict(owner=self.user2.pk),
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ))


# REQUESTS
class RequestsTests(CohortAppTests):
    unupdatable_fields = ["owner", "uuid", "created_at",
                          "modified_at", "deleted", "shared_by"]
    unsettable_default_fields = dict()
    unsettable_fields = ["owner", "uuid", "created_at",
                         "modified_at", "deleted", "shared_by"]
    manual_dupplicated_fields = []

    objects_url = "cohort/requests/"
    retrieve_view = RequestViewSet.as_view({'get': 'retrieve'})
    list_view = RequestViewSet.as_view({'get': 'list'})
    create_view = RequestViewSet.as_view({'post': 'create'})
    delete_view = RequestViewSet.as_view({'delete': 'destroy'})
    update_view = RequestViewSet.as_view({'patch': 'partial_update'})
    model = Request
    model_objects = Request.objects
    model_fields = Request._meta.fields

    def setUp(self):
        super(RequestsTests, self).setUp()
        self.user1_folder1 = Folder.objects.create(owner=self.user1, name="f1")
        self.user2_folder1 = Folder.objects.create(owner=self.user2, name="f1")
        self.user1_folder2 = Folder.objects.create(owner=self.user1, name="f2")
        self.user2_folder2 = Folder.objects.create(owner=self.user2, name="f2")


class RequestsGetTests(RequestsTests):
    def setUp(self):
        super(RequestsGetTests, self).setUp()
        self.str_pattern = "aAa"

        self.requests: List[Request] = []
        for i in range(300):
            u = random.choice([self.user1, self.user2])
            other_u = [i for i in self.users if i != u][0]
            u_folders = list(u.folders.all())

            self.requests.append(Request(
                name=random_str(10, random.random() > .5 and self.str_pattern),
                description=random_str(10, random.random() > .5
                                       and self.str_pattern),
                owner=u,
                favorite=random.random() > .5,
                parent_folder=random.choice(u_folders),
                data_type_of_query=random.choice(REQUEST_DATA_TYPE_CHOICES)[0],
                shared_by=other_u if random.random() > .5 else None,
            ))
        Request.objects.bulk_create(self.requests)

    def test_list(self):
        # As a user, I can list the requests I own
        case = ListCase(
            to_find=[r for r in self.requests if r.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single request I own
        to_find = [f for f in self.requests if f.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single request I do not own
        to_find = [f for f in self.requests if f.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)

    def test_list_with_filters(self):
        # As a user, I can list the requests I own
        basic_case = ListCase(user=self.user1, success=True,
                              status=status.HTTP_200_OK)
        user1_requests = [f for f in self.requests if f.owner == self.user1]
        folder = self.user1.folders.first()
        cases = [
            basic_case.clone(
                params=dict(parent_folder=folder.pk),
                to_find=list(folder.requests.all()),
            ),
            basic_case.clone(
                params=dict(favorite=True),
                to_find=[f for f in user1_requests if f.favorite],
            ),
            basic_case.clone(
                params=dict(data_type_of_query=REQUEST_DATA_TYPE_CHOICES[0][0]),
                to_find=[f for f in user1_requests
                         if (f.data_type_of_query ==
                             REQUEST_DATA_TYPE_CHOICES[0][0])],
            ),
            basic_case.clone(
                params=dict(shared_by=self.user2.pk),
                to_find=[f for f in user1_requests
                         if f.shared_by == self.user2],
            ),
            basic_case.clone(
                params=dict(search=self.str_pattern),
                to_find=[f for f in user1_requests
                         if self.str_pattern.lower()
                         in (f.name + f.description).lower()],
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]

    def test_rest_get_list_from_folder(self):
        # As a user, I can get the list of requests from the Folder they are
        # bound to
        folder = self.user1.folders.first()

        self.check_get_paged_list_case(ListCase(
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
            to_find=list(folder.requests.all())
        ), NestedRequestViewSet.as_view({'get': 'list'}),
            parent_folder=folder.pk)


class RequestsCreateTests(RequestsTests):
    def setUp(self):
        super(RequestsCreateTests, self).setUp()
        self.test_name = "test"
        self.basic_data = dict(
            name=self.test_name,
            parent_folder=self.user1_folder1.pk,
            description="desc",
            favorite=True,
            data_type_of_query=PATIENT_REQUEST_TYPE,
        )
        self.basic_case = CreateCase(
            success=True,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            data=self.basic_data,
            retrieve_filter=RequestCaseRetrieveFilter(name=self.test_name,
                                                      owner=self.user1),
        )

    def test_create(self):
        # As a user, I can create a request
        self.check_create_case(self.basic_case)

    def test_create_with_unread_fields(self):
        # As a user, I can create a request
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1),
                  'shared_by': self.user2.pk},
        ))

    def test_error_create_missing_field(self):
        # As a user, I cannot create a request if some fields are missing
        cases = (self.basic_case.clone(
            data={**self.basic_data, k: None},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ) for k in ['name', 'parent_folder'])
        [self.check_create_case(case) for case in cases]

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a request
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data, 'owner': self.user2.pk},
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
        ))

    def test_error_create_with_forbidden_field(self):
        # As a user, I cannot create a request with some forbidden field/value
        cases = (self.basic_case.clone(
            title=f"with '{k}': {v}",
            data={**self.basic_data, k: v},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            retrieve_filter=FolderCaseRetrieveFilter(
                name=self.test_name,
                owner=self.user1
            ),
        ) for (k, v) in dict(
            parent_folder=self.user2_folder1.pk,
        ).items())
        [self.check_create_case(case) for case in cases]


class RequestsDeleteTests(RequestsTests):
    def setUp(self):
        super(RequestsDeleteTests, self).setUp()
        self.basic_data = dict(
            name="test",
            parent_folder=self.user1_folder1,
            description="desc",
            favorite=True,
            data_type_of_query=PATIENT_REQUEST_TYPE,
            owner=self.user1,
        )
        self.basic_case = DeleteCase(
            data_to_delete=self.basic_data,
            status=status.HTTP_204_NO_CONTENT,
            success=True,
            user=self.user1,
        )

    def test_delete_as_owner(self):
        # As a user, I can delete a request I created
        self.check_delete_case(self.basic_case)

    def test_error_delete_as_not_owner(self):
        # As a user, I cannot delete another user's request
        self.check_delete_case(self.basic_case.clone(
            user=self.user2,
            success=False,
            status=status.HTTP_404_NOT_FOUND,
        ))


class RequestsUpdateTests(RequestsTests):
    def setUp(self):
        super(RequestsUpdateTests, self).setUp()
        self.basic_data = dict(
            name="test",
            parent_folder=self.user1_folder1,
            description="desc",
            favorite=True,
            data_type_of_query=PATIENT_REQUEST_TYPE,
            owner=self.user1,
        )
        self.basic_case = PatchCase(
            data_to_update=dict(),
            initial_data=self.basic_data,
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
        )

    def test_update_as_owner(self):
        # As a user, I can patch a request I own
        self.check_patch_case(self.basic_case.clone(
            data_to_update=dict(
                name="updated",
                parent_folder=self.user1_folder2.pk,
                description="asc",
                favorite=False,
                data_type_of_query=REQUEST_DATA_TYPE_CHOICES[1][0],
                # read_only
                shared_by=self.user2.pk,
                created_at=timezone.now() + timedelta(hours=1),
                modified_at=timezone.now() + timedelta(hours=1),
                deleted=timezone.now() + timedelta(hours=1),
            )
        ))

    def test_error_update_as_not_owner(self):
        # As a user, I cannot patch a request I do not own
        self.check_patch_case(self.basic_case.clone(
            data_to_update=dict(name="new_name"),
            user=self.user2,
            success=False,
            status=status.HTTP_404_NOT_FOUND,
        ))

    def test_error_update_forbidden_fields(self):
        # As a user, I cannot patch a folder I with forbidden values
        cases = (self.basic_case.clone(
            data_to_update={k: v},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ) for (k, v) in dict(
            owner=self.user2.pk,
            parent_folder=self.user2_folder1.pk,
        ).items())
        [self.check_patch_case(case) for case in cases]


# REQUEST_QUERY_SNAPSHOTS


class RqsCreateCase(CreateCase):
    def __init__(self, mock_fhir_resp: any, mock_fhir_called: bool, **kwargs):
        super(RqsCreateCase, self).__init__(**kwargs)
        self.mock_fhir_resp = mock_fhir_resp
        self.mock_fhir_called = mock_fhir_called


class ShareCase(RequestCase):
    def __init__(self, initial_data: dict, recipients: List[User],
                 new_name: str = None, **kwargs):
        super(ShareCase, self).__init__(**kwargs)
        self.initial_data = initial_data
        self.recipients = recipients
        self.new_name = new_name

    @property
    def description_dict(self) -> dict:
        d = {
            **self.__dict__,
            'user': self.user and self.user.displayed_name,
            'recipients': [str(user) for user in self.recipients or []],
        }
        d.pop('title', None)
        return d


class RqsTests(RequestsTests):
    unupdatable_fields = ["owner", "request", "uuid", "previous_snapshot",
                          "shared_by", "is_active_branch",
                          "created_at", "modified_at", "deleted"]
    unsettable_default_fields = dict()
    unsettable_fields = ["owner", "uuid", "shared_by", "is_active_branch",
                         "created_at", "modified_at", "deleted", ]
    manual_dupplicated_fields = []

    objects_url = "cohort/request-query-snapshots/"
    retrieve_view = RequestQuerySnapshotViewSet.as_view({'get': 'retrieve'})
    list_view = RequestQuerySnapshotViewSet.as_view({'get': 'list'})
    create_view = RequestQuerySnapshotViewSet.as_view({'post': 'create'})
    delete_view = RequestQuerySnapshotViewSet.as_view({'delete': 'destroy'})
    update_view = RequestQuerySnapshotViewSet.as_view(
        {'patch': 'partial_update'})
    share_view = RequestQuerySnapshotViewSet.as_view({'post': 'share'})
    model = RequestQuerySnapshot
    model_objects = RequestQuerySnapshot.objects
    model_fields = RequestQuerySnapshot._meta.fields

    def setUp(self):
        super(RqsTests, self).setUp()
        self.user1_req1 = Request.objects.create(
            owner=self.user1,
            name="Request 1",
            description="Request 1 from user 1",
            parent_folder=self.user1_folder1
        )
        self.user1_req2 = Request.objects.create(
            owner=self.user1,
            name="Request 2",
            description="Request 2 from user 1",
            parent_folder=self.user1_folder2
        )
        self.user2_req1 = Request.objects.create(
            owner=self.user2,
            name="Request 1",
            description="Request 1 from user 2",
            parent_folder=self.user2_folder1
        )
        self.user2_req2 = Request.objects.create(
            owner=self.user2,
            name="Request 2",
            description="Request 2 from user 2",
            parent_folder=self.user2_folder2
        )
        self.requests = [self.user1_req1, self.user1_req2,
                         self.user2_req1, self.user2_req2]


class RqsGetTests(RqsTests):
    def setUp(self):
        super(RqsGetTests, self).setUp()
        self.str_pattern = "aAa"
        self.folders: List[Folder] = sum((list(u.folders.all())
                                          for u in self.users), [])
        base_rqss: List[RequestQuerySnapshot] = []

        def random_json():
            return (f'{"{"}"{random_str(5)}": "'
                    + random_str(20, random.random() > .5 and self.str_pattern)
                    + '"}')

        for r in self.requests:
            base_rqss.append(RequestQuerySnapshot(
                owner=r.owner,
                request=r,
                serialized_query=random_json(),
                shared_by=(next(u for u in self.users if u != r.owner)
                           if random.random() > .5 else None),
                is_active_branch=random.random() > .5,
            ))
        RequestQuerySnapshot.objects.bulk_create(base_rqss)

        new_rqss: List[RequestQuerySnapshot] = []
        for i in range(300):
            prev = random.choice(base_rqss)
            new_rqss.append(RequestQuerySnapshot(
                owner=prev.owner,
                request=prev.request,
                serialized_query=random_json(),
                shared_by=(next(u for u in self.users if u != prev.owner)
                           if random.random() > .5 else None),
                is_active_branch=prev.is_active_branch and random.random() > .2,
            ))
        RequestQuerySnapshot.objects.bulk_create(new_rqss)
        self.rqss = base_rqss + new_rqss

    def test_list(self):
        # As a user, I can list the RQS I own
        case = ListCase(
            to_find=[r for r in self.rqss if r.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single RQS I own
        to_find = [f for f in self.rqss if f.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single RQS I do not own
        to_find = [f for f in self.rqss if f.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)

    def test_list_with_filters(self):
        # As a user, I can list the RQSs I own applying filters
        basic_case = ListCase(user=self.user1, success=True,
                              status=status.HTTP_200_OK)
        user1_rqss = [f for f in self.rqss if f.owner == self.user1]
        folder = self.user1.folders.first()
        req = folder.requests.first()
        prev_rqs = req.query_snapshots.first()
        cases = [
            basic_case.clone(
                params=dict(is_active_branch=True),
                to_find=[rqs for rqs in user1_rqss if rqs.is_active_branch],
            ),
            basic_case.clone(
                params=dict(shared_by=self.user2.pk),
                to_find=[rqs for rqs in user1_rqss
                         if rqs.shared_by == self.user2],
            ),
            basic_case.clone(
                params=dict(search=self.str_pattern),
                to_find=[rqs for rqs in user1_rqss
                         if self.str_pattern.lower()
                         in rqs.serialized_query.lower()],
            ),
            basic_case.clone(
                params=dict(previous_snapshot=prev_rqs.pk),
                to_find=list(prev_rqs.next_snapshots.all()),
            ),
            basic_case.clone(
                params=dict(request=req.pk),
                to_find=list(req.query_snapshots.all()),
            ),
            basic_case.clone(
                params=dict(request__parent_folder=folder.pk),
                to_find=sum((list(r.query_snapshots.all())
                             for r in folder.requests.all()), []),
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]

    def test_rest_get_list_from_request(self):
        # As a user, I can get the list of RQSs from the request they are
        # bound to
        req = self.user1.folders.first().requests.first()

        self.check_get_paged_list_case(ListCase(
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
            to_find=list(req.query_snapshots.all())
        ), NestedRqsViewSet.as_view({'get': 'list'}), request_id=req.pk)

    def test_rest_get_list_from_previous_rqs(self):
        # As a user, I can get the list of RQSs from the previous RQS they are
        # bound to
        prev_rqs = self.user1.folders.first().requests.first() \
            .query_snapshots.first()

        self.check_get_paged_list_case(ListCase(
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
            to_find=list(prev_rqs.next_snapshots.all())
        ), NestedRqsViewSet.as_view({'get': 'list'}),
            previous_snapshot=prev_rqs.pk)


class RqsCreateTests(RqsTests):
    @mock.patch('cohort.serializers.conf.get_fhir_authorization_header')
    @mock.patch('cohort.serializers.conf.post_validate_cohort')
    def check_create_case_with_mock(
            self, case: RqsCreateCase, mock_validate: MagicMock,
            mock_header: MagicMock, other_view: any, view_kwargs: dict):
        mock_header.return_value = None
        mock_validate.return_value = case.mock_fhir_resp

        super(RqsCreateTests, self).check_create_case(
            case, other_view, **(view_kwargs or {}))

        mock_validate.assert_called() if case.mock_fhir_called \
            else mock_validate.assert_not_called()

        if case.success:
            # we check that the new rqs is the only with active_branch True,
            # among other 'next_snapshots' from the previous one
            rqs: RequestQuerySnapshot = self.model_objects.filter(
                **case.retrieve_filter.args).first()
            if rqs.previous_snapshot:
                self.assertTrue(all(
                    not r.is_active_branch for r in
                    rqs.previous_snapshot.next_snapshots.exclude(pk=rqs.pk)
                ))

    def check_create_case(self, case: RqsCreateCase, other_view: any = None,
                          **view_kwargs):
        return self.check_create_case_with_mock(
            case, other_view=other_view or None, view_kwargs=view_kwargs)

    def setUp(self):
        super(RqsCreateTests, self).setUp()
        #          user1_snap1
        #           /       \
        # user1_b1_snap2  user1_b2_snap2 (active) (saved)
        #                         |
        #                 user1_b2_snap3 (active)

        self.user1_req1_snap1 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
        )
        self.user1_req1_branch1_snap2 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            previous_snapshot=self.user1_req1_snap1,
            serialized_query='{"perimeter": "Terra"}',
            is_active_branch=True,
        )

        self.test_query = '{"test": "query"}'
        self.basic_data = dict(
            request=self.user1_req2.pk,
            serialized_query=self.test_query,
        )
        self.basic_case = RqsCreateCase(
            success=True,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            data=self.basic_data,
            retrieve_filter=RQSCaseRetrieveFilter(
                serialized_query=self.test_query),
            mock_fhir_resp=FhirValidateResponse(True),
            mock_fhir_called=True,
        )
        self.basic_err_case = self.basic_case.clone(
            mock_fhir_called=False,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def test_create(self):
        # As a user, I can create a RQS
        self.check_create_case(self.basic_case)

    def test_create_from_request(self):
        # As a user, I can create a RQS
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data, 'request': None}
        ), NestedRqsViewSet.as_view({'post': 'create'}),
            request_id=self.user1_req2.pk)

    def test_create_with_unread_fields(self):
        # As a user, I can create a request
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'is_active_branch': False,
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1),
                  'shared_by': self.user2.pk},
        ))

    def test_create_on_previous(self):
        # As a user, I can create a RQS specifying a previous snapshot
        self.check_create_case(self.basic_case.clone(
            data={'serialized_query': self.test_query,
                  'previous_snapshot': self.user1_req1_snap1.pk},
        ))

    def test_create_from_previous(self):
        # As a user, I can create a RQS specifying a previous snapshot
        # using nestedViewSet
        self.check_create_case(self.basic_case.clone(
            data={'serialized_query': self.test_query},
        ), NestedRqsViewSet.as_view({'post': 'create'}),
            previous_snapshot=self.user1_req1_snap1.pk)

    def test_error_create_missing_field(self):
        # As a user, I cannot create a folder if some fields are missing
        cases = (self.basic_err_case.clone(
            data={**self.basic_data, k: None},
        ) for k in ['serialized_query'])
        [self.check_create_case(case) for case in cases]

    def test_error_create_missing_both_request_previous(self):
        # As a user, I cannot create a RQS not specifying either
        # previous snapshot or request
        self.check_create_case(self.basic_err_case.clone(
            data=dict(serialized_query=self.test_query),
        ))

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a RQS providing another user as owner
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'owner': self.user2.pk},
        ))

    def test_error_create_with_not_owned_request(self):
        # As a user, I cannot create a RQS providing another user as owner
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'request': self.user2_req1.pk},
        ))

    def test_error_create_unmatching_request_previous(self):
        # As a user, I cannot create a RQS providing both request
        # and previous_snapshot if thei are not bound to each other
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data,
                  'previous_snapshot': self.user1_req1_snap1.pk},
        ))

    def test_error_create_missing_previous_if_request_not_empty(self):
        # As a user, I cannot create a RQS not specifying either
        # previous snapshot if the request alreay has query_snapshots
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'request': self.user1_req1.pk},
        ))

    def test_error_create_unvalid_query(self):
        # As a user, I cannot create a RQS if the query server deny the query
        # or the query is not a json
        cases = (self.basic_err_case.clone(
            mock_fhir_resp=FhirValidateResponse(False),
            mock_fhir_called=True,
        ), self.basic_err_case.clone(
            data={**self.basic_data, 'serialized_query': "not_json"},
            retrieve_filter=RQSCaseRetrieveFilter(
                serialized_query="not_json"),
        ))
        [self.check_create_case(case) for case in cases]

    # def test_error_create_with_forbidden_field(self):
    #     # As a user, I cannot create a request with some forbidden field/value
    #     cases = (self.basic_case.clone(
    #         title=f"with '{k}': {v}",
    #         data={**self.basic_data, k: v},
    #         success=False,
    #         status=status.HTTP_400_BAD_REQUEST,
    #     ) for (k, v) in dict(
    #         parent_folder=self.user2_folder1.pk,
    #     ).items())
    #     [self.check_create_case(case) for case in cases]


class RqsShareTests(RqsTests):
    def setUp(self):
        super(RqsShareTests, self).setUp()
        self.user1_req1_snapshot1 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            serialized_query="{}",
        )

        self.basic_case = ShareCase(
            initial_data=dict(
                owner=self.user1, request=self.user1_req1,
                previous_snapshot=self.user1_req1_snapshot1,
                serialized_query='{"test": "success"}',
            ),
            success=True,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            recipients=[self.user2, self.user1],
        )

    def check_share_case(self, case: ShareCase, ):
        obj = RequestQuerySnapshot.objects.create(**case.initial_data)

        data = dict(recipients=",".join([u.pk for u in case.recipients or []]))
        if case.new_name:
            data['name'] = case.new_name

        request = self.factory.post(f"{self.objects_url}/{obj.pk}/share",
                                    data=data, format='json')
        if case.user:
            force_authenticate(request, case.user)

        response = self.__class__.share_view(request, uuid=obj.pk)
        response.render()

        msg = (f"{case.description}"
               + (f" -> {prettify_json(response.content)}"
                  if response.content else ""))
        self.assertEqual(response.status_code, case.status, msg=msg)

        if case.success:
            for u in case.recipients:
                rqs = RequestQuerySnapshot.objects.filter(
                    request__parent_folder__name=SHARED_FOLDER_NAME,
                    request__name=case.new_name or obj.request.name,
                    request__shared_by=case.user,
                    previous_snapshot__isnull=True,
                    owner=u,
                    shared_by=case.user
                ).first()
                self.assertIsNotNone(rqs, msg=f"Recipient: {u} - {msg}")
        else:
            if case.recipients is not None:
                self.assertIsNone(RequestQuerySnapshot.objects.filter(
                    owner__in=case.recipients,
                    shared_by=case.user
                ).first(), msg=msg)

    def test_share_rqs(self):
        # As a user, I can share a request query snapshot to other users
        # (including myself). It will create new requests,
        # with RQSs, all with shared_by=me
        self.check_share_case(self.basic_case)

    def test_share_rqs_with_new_name(self):
        # As a user, I can share a request query snapshot to other users
        # providing a new name
        self.check_share_case(self.basic_case.clone(
            new_name="new_request",
        ))

    def test_error_share_unknown_users(self):
        # As a user, I cannot share a RQS with not existing recipients
        self.check_share_case(self.basic_case.clone(
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
            recipients=[self.user2, User(pk="wrong", email="n@aphp.fr",
                                         firstname="not", lastname="existing")]
        ))

    def test_error_missing_recipients(self):
        # As a user, I cannot share a RQS without recipients
        self.check_share_case(self.basic_case.clone(
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
            recipients=None
        ))


class RqsDeleteTests(RqsTests):
    def test_error_delete_rqs(self):
        # As a user, I cannot delete a rqs, even if I own it
        self.check_delete_case(DeleteCase(
            data_to_delete=dict(
                request=self.user1_req2,
                serialized_query="{}",
                owner=self.user1,
            ),
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            success=False,
            user=self.user1,
        ))


class RqsUpdateTests(RqsTests):
    def test_error_update_rqs(self):
        # As a user, I cannot update a rqs, even if I own it
        self.check_patch_case(PatchCase(
            initial_data=dict(
                request=self.user1_req2,
                serialized_query="{}",
                owner=self.user1,
            ),
            data_to_update=dict(serialized_query="{}"),
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
            success=False,
            user=self.user1,
        ))


# DATED_MEASURES


class DatedMeasuresTests(RqsTests):
    unupdatable_fields = ["owner", "request_query_snapshot", "uuid",
                          "mode", "count_task_id", "fhir_datetime",
                          "measure", "measure_min", "measure_max",
                          "measure_male", "measure_unknown", "measure_deceased",
                          "measure_alive", "measure_female",
                          "created_at", "modified_at", "deleted"]
    unsettable_default_fields = dict(
        request_job_status=JobStatus.new)
    unsettable_fields = ["owner", "uuid", "count_task_id",
                         "created_at", "modified_at", "deleted", ]
    manual_dupplicated_fields = []

    objects_url = "cohort/dated-measures/"
    retrieve_view = DatedMeasureViewSet.as_view({'get': 'retrieve'})
    list_view = DatedMeasureViewSet.as_view({'get': 'list'})
    create_view = DatedMeasureViewSet.as_view({'post': 'create'})
    delete_view = DatedMeasureViewSet.as_view({'delete': 'destroy'})
    update_view = DatedMeasureViewSet.as_view(
        {'patch': 'partial_update'})
    model = DatedMeasure
    model_objects = DatedMeasure.objects
    model_fields = DatedMeasure._meta.fields

    def setUp(self):
        super(DatedMeasuresTests, self).setUp()

        self.user1_req1_snap1 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            serialized_query='{}',
        )
        self.user1_req1_branch1_snap2 = RequestQuerySnapshot.objects.create(
            owner=self.user1,
            request=self.user1_req1,
            previous_snapshot=self.user1_req1_snap1,
            serialized_query='{"perimeter": "Terra"}',
            is_active_branch=True,
        )
        self.user2_req1_snap1 = RequestQuerySnapshot.objects.create(
            owner=self.user2,
            request=self.user2_req1,
            serialized_query='{}',
        )


class DatedMeasuresGetTests(DatedMeasuresTests):
    def setUp(self):
        super(DatedMeasuresGetTests, self).setUp()
        self.rqss: List[RequestQuerySnapshot] = sum((list(
            u.user_request_query_snapshots.all()) for u in self.users), [])

        to_create: List[DatedMeasure] = []
        for i in range(200):
            rqs = random.choice(self.rqss)
            to_create.append(DatedMeasure(
                request_query_snapshot=rqs,
                owner=rqs.owner,
                measure=random.randint(0, 20),
                mode=random.choice(DATED_MEASURE_MODE_CHOICES)[0],
                count_task_id=random_str(15),
            ))

        self.dms: List[DatedMeasure] = DatedMeasure.objects.bulk_create(
            to_create)

    def test_list(self):
        # As a user, I can list the DM I own
        case = ListCase(
            to_find=[dm for dm in self.dms if dm.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single DM I own
        to_find = [dm for dm in self.dms if dm.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single DM I do not own
        to_find = [dm for dm in self.dms if dm.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)

    def test_list_with_filters(self):
        # As a user, I can list the DMs I own applying filters
        basic_case = ListCase(user=self.user1, success=True,
                              status=status.HTTP_200_OK)
        rqs = self.user1.user_request_query_snapshots.first()
        req = rqs.request
        first_dm = self.user1.user_request_query_results.first()
        cases = [
            basic_case.clone(
                params=dict(count_task_id=first_dm.count_task_id),
                to_find=[first_dm],
            ),
            basic_case.clone(
                params=dict(mode=DATED_MEASURE_MODE_CHOICES[0][0]),
                to_find=[dm for dm in
                         self.user1.user_request_query_results.all()
                         if dm.mode == DATED_MEASURE_MODE_CHOICES[0][0]],
            ),
            basic_case.clone(
                params=dict(request_query_snapshot=rqs.pk),
                to_find=list(rqs.dated_measures.all()),
            ),
            basic_case.clone(
                params=dict(request_query_snapshot__request=req.pk),
                to_find=sum((list(rqs.dated_measures.all())
                             for rqs in req.query_snapshots.all()), []),
            ),
            basic_case.clone(
                params=dict(request_id=req.pk),
                to_find=sum((list(rqs.dated_measures.all())
                             for rqs in req.query_snapshots.all()), []),
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]

    def test_rest_get_list_from_rqs(self):
        # As a user, I can get the list of DMs from the RQS it is bound to
        rqs = self.user1.user_request_query_snapshots.first()

        self.check_get_paged_list_case(ListCase(
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
            to_find=list(rqs.dated_measures.all())
        ), NestedDatedMeasureViewSet.as_view({'get': 'list'}),
            request_query_snapshot=rqs.pk)


class DMCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, request_query_snapshot__pk: str = "", **kwargs):
        self.request_query_snapshot__pk = request_query_snapshot__pk
        super(DMCaseRetrieveFilter, self).__init__(**kwargs)


class DMCreateCase(CreateCase):
    def __init__(self, mock_task_called: bool, **kwargs):
        super(DMCreateCase, self).__init__(**kwargs)
        self.mock_task_called = mock_task_called


class DatedMeasuresCreateTests(DatedMeasuresTests):
    @mock.patch('cohort.serializers.conf.get_fhir_authorization_header')
    @mock.patch('cohort.serializers.conf.format_json_request')
    @mock.patch('cohort.tasks.get_count_task.delay')
    def check_create_case_with_mock(
            self, case: DMCreateCase, mock_task: MagicMock,
            mock_json: MagicMock, mock_header: MagicMock, other_view: any,
            view_kwargs: dict):
        mock_header.return_value = None
        mock_task.return_value = None
        mock_json.return_value = None

        super(DatedMeasuresCreateTests, self).check_create_case(
            case, other_view, **(view_kwargs or {}))

        mock_task.assert_called() if case.mock_task_called \
            else mock_task.assert_not_called()
        mock_header.assert_called() if case.mock_task_called \
            else mock_header.assert_not_called()
        mock_json.assert_called() if case.mock_task_called \
            else mock_json.assert_not_called()

    def check_create_case(self, case: DMCreateCase, other_view: any = None,
                          **view_kwargs):
        return self.check_create_case_with_mock(
            case, other_view=other_view or None, view_kwargs=view_kwargs)

    def setUp(self):
        super(DatedMeasuresCreateTests, self).setUp()

        self.basic_data = dict(
            request_query_snapshot=self.user1_req1_snap1.pk,
            mode=DATED_MEASURE_MODE_CHOICES[0][0],
        )
        self.basic_case = DMCreateCase(
            data=self.basic_data,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            success=True,
            mock_task_called=True,
            retrieve_filter=DMCaseRetrieveFilter(
                request_query_snapshot__pk=self.user1_req1_snap1.pk)
        )
        self.basic_err_case = self.basic_case.clone(
            mock_task_called=False,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def test_create(self):
        # As a user, I can create a DatedMeasure with only RQS,
        # it will launch a task
        self.check_create_case(self.basic_case)

    def test_create_with_data(self):
        # As a user, I can create a DatedMeasure with all fields,
        # no task will be launched
        self.check_create_case(self.basic_case.clone(
            data={
                **self.basic_data,
                'measure': 1,
                'measure_min': 1,
                'measure_max': 1,
                'measure_male': 1,
                'measure_unknown': 1,
                'measure_deceased': 1,
                'measure_alive': 1,
                'measure_female': 1,
                'fhir_datetime': timezone.now(),
            },
            mock_task_called=False,
        ))

    def test_create_with_unread_fields(self):
        # As a user, I can create a dm
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'request_job_fail_msg': "test",
                  'request_job_id': "test",
                  'count_task_id': "test",
                  'request_job_duration': '1',
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1)},
        ))

    def test_error_create_missing_time_or_measure(self):
        # As a user, I cannot create a dm if I provide one of fhir_datetime
        # and measure but not both
        cases = (self.basic_err_case.clone(
            data={**self.basic_data, k: v},
        ) for (k, v) in {'fhir_datetime': timezone.now(), 'measure': 1}.items())
        [self.check_create_case(case) for case in cases]

    def test_error_create_missing_field(self):
        # As a user, I cannot create a dm if some field is missing
        cases = (self.basic_err_case.clone(
            data={**self.basic_data, k: None},
        ) for k in ['request_query_snapshot'])
        [self.check_create_case(case) for case in cases]

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a DM providing another user as owner
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'owner': self.user2.pk},
        ))

    # def test_error_create_with_forbidden_field(self):
    #     # As a user, I cannot create a request with some forbidden field/value
    #     cases = (self.basic_case.clone(
    #         title=f"with '{k}': {v}",
    #         data={**self.basic_data, k: v},
    #         success=False,
    #         status=status.HTTP_400_BAD_REQUEST,
    #         retrieve_filter=FolderCaseRetrieveFilter(
    #             name=self.test_name,
    #             owner=self.user1
    #         ),
    #     ) for (k, v) in dict(
    #         request_query_snapshot=self.user2_req1_snap1.pk,
    #     ).items())
    #     [self.check_create_case(case) for case in cases]

    def test_create_from_rqs(self):
        # As a user, I can create a RQS specifying a previous snapshot
        # using nestedViewSet
        self.check_create_case(self.basic_case.clone(
            data={},
        ), NestedDatedMeasureViewSet.as_view({'post': 'create'}),
            request_query_snapshot=self.user1_req1_snap1.pk)

    def test_error_create_on_rqs_not_owned(self):
        # As a user, I cannot create a dm on a Rqs I don't own
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data,
                  'request_query_snapshot': self.user2_req1_snap1.pk},
        ))


class DMDeleteCase(DeleteCase):
    def __init__(self, with_cohort: bool = False, **kwargs):
        super(DMDeleteCase, self).__init__(**kwargs)
        self.with_cohort = with_cohort


class DatedMeasuresDeleteTests(DatedMeasuresTests):
    def check_delete_case(self, case: DMDeleteCase):
        obj = self.model_objects.create(**case.data_to_delete)

        if case.with_cohort:
            CohortResult.objects.create(
                dated_measure=obj,
                request_query_snapshot=obj.request_query_snapshot,
                owner=obj.owner,
            )

        request = self.factory.delete(self.objects_url)
        force_authenticate(request, case.user)
        response = self.__class__.delete_view(
            request, **{self.model._meta.pk.name: obj.pk}
        )
        response.render()

        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.description}"
                 + (f" -> {prettify_json(response.content)}"
                    if response.content else "")),
        )

        obj = self.model.all_objects.filter(pk=obj.pk).first()

        if case.success:
            self.check_is_deleted(obj)
        else:
            self.assertIsNotNone(obj)
            self.assertIsNone(obj.deleted)
            obj.delete()

    def setUp(self):
        super(DatedMeasuresDeleteTests, self).setUp()
        self.basic_data = dict(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            fhir_datetime=timezone.now(),
            measure=1,
            measure_min=1,
            measure_max=1,
            measure_male=1,
            measure_unknown=1,
            measure_deceased=1,
            measure_alive=1,
            measure_female=1,
            count_task_id="test",
            mode=DATED_MEASURE_MODE_CHOICES[0][0],
            created_at=timezone.now(),
            modified_at=timezone.now(),
            request_job_id="test",
            request_job_status=JobStatus.pending.name,
            request_job_fail_msg="test",
            request_job_duration="1s",
        )
        self.basic_case = DMDeleteCase(
            data_to_delete=self.basic_data,
            status=status.HTTP_204_NO_CONTENT,
            success=True,
            user=self.user1,
        )
        self.basic_err_case = self.basic_case.clone(
            status=status.HTTP_403_FORBIDDEN,
            success=False,
            user=self.user1,
        )

    def test_delete_owned_dm_without_cohort(self):
        # As a user, I can delete a dated measure I owned,
        # not bound to a CohortResult
        self.check_delete_case(self.basic_case)

    def test_error_delete_owned_dm_with_cohort(self):
        # As a user, I cannot delete a dated measure bound to a CohortResult
        self.check_delete_case(self.basic_err_case.clone(
            with_cohort=True
        ))

    def test_error_delete_not_owned(self):
        # As a user, I cannot delete a dated measure linekd to a CohortResult
        self.check_delete_case(self.basic_err_case.clone(
            user=self.user2,
            status=status.HTTP_404_NOT_FOUND,
        ))


class DatedMeasuresUpdateTests(DatedMeasuresTests):
    def setUp(self):
        super(DatedMeasuresUpdateTests, self).setUp()
        self.basic_data = dict(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            fhir_datetime=timezone.now(),
            measure=1,
            measure_min=1,
            measure_max=1,
            measure_male=1,
            measure_unknown=1,
            measure_deceased=1,
            measure_alive=1,
            measure_female=1,
            count_task_id="test",
            mode=DATED_MEASURE_MODE_CHOICES[0][0],
            created_at=timezone.now(),
            modified_at=timezone.now(),
            request_job_id="test",
            request_job_status=JobStatus.pending.name,
            request_job_fail_msg="test",
            request_job_duration="1s",
        )
        self.basic_err_case = PatchCase(
            data_to_update=dict(measure=10),
            initial_data=self.basic_data,
            status=status.HTTP_403_FORBIDDEN,
            success=False,
            user=self.user1,
        )

    def test_error_update(self):
        # As a user, I cannot update a DatedMeasure I own
        self.check_patch_case(self.basic_err_case)

    def test_error_update_dm_as_not_owner(self):
        # As a user, I cannot update a dated_measure I don't own
        self.check_patch_case(self.basic_err_case.clone(
            status=status.HTTP_403_FORBIDDEN,
            initial_data={**self.basic_data, 'owner': self.user2}
        ))


# COHORTS


class CohortsTests(DatedMeasuresTests):
    unupdatable_fields = ["owner", "request_query_snapshot", "uuid",
                          "type", "create_task_id", "dated_measure",
                          "request_job_id", "request_job_status",
                          "request_job_fail_msg", "request_job_duration",
                          "created_at", "modified_at", "deleted"]
    unsettable_default_fields = dict(request_job_status=JobStatus.new)
    unsettable_fields = ["owner", "uuid", "create_task_id",
                         "created_at", "modified_at", "deleted", ]
    manual_dupplicated_fields = []

    objects_url = "cohort/cohorts/"
    retrieve_view = CohortResultViewSet.as_view({'get': 'retrieve'})
    list_view = CohortResultViewSet.as_view({'get': 'list'})
    create_view = CohortResultViewSet.as_view({'post': 'create'})
    delete_view = CohortResultViewSet.as_view({'delete': 'destroy'})
    update_view = CohortResultViewSet.as_view(
        {'patch': 'partial_update'})
    model = CohortResult
    model_objects = CohortResult.objects
    model_fields = CohortResult._meta.fields

    def setUp(self):
        super(CohortsTests, self).setUp()


class CohortsGetTests(CohortsTests):
    def setUp(self):
        super(CohortsGetTests, self).setUp()
        self.rqss: List[RequestQuerySnapshot] = sum((list(
            u.user_request_query_snapshots.all()) for u in self.users), [])
        self.str_pattern = "aAa"

        to_create: List[DatedMeasure] = []
        crs_to_create: List[CohortResult] = []
        for i in range(200):
            rqs = random.choice(self.rqss)
            dm = DatedMeasure(
                request_query_snapshot=rqs,
                owner=rqs.owner,
                measure=random.randint(0, 20),
                mode=SNAPSHOT_DM_MODE,
                count_task_id=random_str(15),
                fhir_datetime=(timezone.now()
                               - timedelta(days=random.randint(1, 5))),
            )
            to_create.append(dm)

            dm_global = None
            if random.random() > .5:
                dm_global = DatedMeasure(
                    request_query_snapshot=rqs,
                    owner=rqs.owner,
                    measure=random.randint(0, 20),
                    mode=GLOBAL_DM_MODE,
                    count_task_id=random_str(15),
                )
                to_create.append(dm_global)

            crs_to_create.append(CohortResult(
                owner=dm.owner,
                name=random_str(10, random.random() > .5
                                and self.str_pattern),
                description=random_str(10, random.random() > .5
                                       and self.str_pattern),
                favorite=random.random() > .5,
                request_query_snapshot=dm.request_query_snapshot,
                fhir_group_id=random_str(10, with_space=False),
                request_job_status=random.choice(JobStatus.list()),
                dated_measure=dm,
                dated_measure_global=dm_global,
                create_task_id=random_str(10),
            ))

        self.dms: List[DatedMeasure] = DatedMeasure.objects.bulk_create(
            to_create)
        self.crs: List[CohortResult] = CohortResult.objects.bulk_create(
            crs_to_create)

    def test_list(self):
        # As a user, I can list the CR I own
        case = ListCase(
            to_find=[cr for cr in self.crs if cr.owner == self.user1],
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_get_paged_list_case(case)

    def test_retrieve(self):
        # As a user, I can retrieve a single CR I own
        to_find = [cr for cr in self.crs if cr.owner == self.user1][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=True,
            status=status.HTTP_200_OK
        )
        self.check_retrieve_case(case)

    def test_error_get_not_owned(self):
        # As a user, I cannot retrieve a single CR I do not own
        to_find = [cr for cr in self.crs if cr.owner == self.user2][0]
        case = RetrieveCase(
            to_find=to_find,
            view_params=dict(uuid=to_find.pk),
            user=self.user1,
            success=False,
            status=status.HTTP_404_NOT_FOUND
        )
        self.check_retrieve_case(case)

    def test_list_with_filters(self):
        # As a user, I can list the CRs I own applying filters
        basic_case = ListCase(user=self.user1, success=True,
                              status=status.HTTP_200_OK)
        crs = [cr for cr in self.crs if cr.owner == self.user1]
        rqs = self.user1.user_request_query_snapshots.first()
        req = rqs.request
        first_cr: CohortResult = self.user1.user_cohorts.first()
        example_measure = 10
        example_datetime = timezone.now() - timedelta(days=2)

        cases = [
            basic_case.clone(
                params=dict(request_job_status=JobStatus.pending.value),
                to_find=[cr for cr in crs
                         if cr.request_job_status == JobStatus.pending],
            ),
            basic_case.clone(
                params=dict(name=self.str_pattern),
                to_find=[cr for cr in crs
                         if self.str_pattern.lower() in cr.name.lower()],
            ),
            basic_case.clone(
                params=dict(min_result_size=example_measure),
                to_find=[cr for cr in crs
                         if cr.dated_measure.measure >= example_measure],
            ),
            basic_case.clone(
                params=dict(max_result_size=example_measure),
                to_find=[cr for cr in crs
                         if cr.dated_measure.measure <= example_measure],
            ),
            basic_case.clone(
                params=dict(min_fhir_datetime=example_datetime.isoformat()),
                to_find=[cr for cr in crs if
                         cr.dated_measure.fhir_datetime >= example_datetime],
            ),
            basic_case.clone(
                params=dict(max_fhir_datetime=example_datetime.isoformat()),
                to_find=[cr for cr in crs if
                         cr.dated_measure.fhir_datetime <= example_datetime],
            ),
            basic_case.clone(
                params=dict(favorite=True),
                to_find=[cr for cr in crs if cr.favorite],
            ),
            basic_case.clone(
                params=dict(fhir_group_id=first_cr.fhir_group_id),
                to_find=[first_cr],
            ),
            basic_case.clone(
                params=dict(create_task_id=first_cr.create_task_id),
                to_find=[first_cr],
            ),
            basic_case.clone(
                params=dict(request_query_snapshot=rqs.pk),
                to_find=list(rqs.cohort_results.all()),
            ),
            basic_case.clone(
                params=dict(request_query_snapshot__request=req.pk),
                to_find=sum((list(rqs.cohort_results.all())
                             for rqs in req.query_snapshots.all()), []),
            ),
            basic_case.clone(
                params=dict(request_id=req.pk),
                to_find=sum((list(rqs.cohort_results.all())
                             for rqs in req.query_snapshots.all()), []),
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]

    def test_rest_get_list_from_rqs(self):
        # As a user, I can get the list of CRs from the RQS it is bound to
        rqs = self.user1.user_request_query_snapshots.first()

        self.check_get_paged_list_case(ListCase(
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
            to_find=list(rqs.cohort_results.all())
        ), NestedCohortResultViewSet.as_view({'get': 'list'}),
            request_query_snapshot=rqs.pk)


class CohortCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str = "", **kwargs):
        self.name = name
        super(CohortCaseRetrieveFilter, self).__init__(**kwargs)


class CohortCreateCase(CreateCase):
    def __init__(self, mock_task_called: bool, **kwargs):
        super(CohortCreateCase, self).__init__(**kwargs)
        self.mock_task_called = mock_task_called


class CohortsCreateTests(CohortsTests):
    @mock.patch('cohort.serializers.conf.get_fhir_authorization_header')
    @mock.patch('cohort.serializers.conf.format_json_request')
    @mock.patch('cohort.tasks.create_cohort_task.delay')
    @mock.patch('cohort.tasks.get_count_task.delay')
    def check_create_case_with_mock(
            self, case: CohortCreateCase, mock_task_count: MagicMock,
            mock_task: MagicMock, mock_json: MagicMock, mock_header: MagicMock,
            other_view: any, view_kwargs: dict):
        mock_header.return_value = None
        mock_task.return_value = None
        mock_json.return_value = None
        mock_task_count.return_value = None

        super(CohortsCreateTests, self).check_create_case(
            case, other_view, **(view_kwargs or {}))

        if case.success:
            inst = self.model_objects.filter(**case.retrieve_filter.args) \
                .exclude(**case.retrieve_filter.exclude).first()
            self.assertIsNotNone(inst.dated_measure)

            if case.data.get('global_estimate', False):
                self.assertIsNotNone(inst.dated_measure_global)

                mock_task.assert_called() if case.mock_task_called \
                    else mock_task.assert_not_called()

        mock_task.assert_called() if case.mock_task_called \
            else mock_task.assert_not_called()
        mock_header.assert_called() if case.mock_task_called \
            else mock_header.assert_not_called()
        mock_json.assert_called() if case.mock_task_called \
            else mock_json.assert_not_called()

    def check_create_case(self, case: CohortCreateCase, other_view: any = None,
                          **view_kwargs):
        return self.check_create_case_with_mock(
            case, other_view=other_view or None, view_kwargs=view_kwargs)

    def setUp(self):
        super(CohortsCreateTests, self).setUp()

        self.test_name = "test"

        self.basic_data = dict(
            name=self.test_name,
            description=self.test_name,
            favorite=True,
            request_query_snapshot=self.user1_req1_snap1.pk,
            # fhir_group_id
            # dated_measure
            # dated_measure_global
            # create_task_id
            # type
        )
        self.basic_case = CohortCreateCase(
            data=self.basic_data,
            status=status.HTTP_201_CREATED,
            user=self.user1,
            success=True,
            mock_task_called=True,
            retrieve_filter=CohortCaseRetrieveFilter(name=self.test_name),
            global_estimate=False
        )
        self.basic_err_case = self.basic_case.clone(
            mock_task_called=False,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )

    def test_create(self):
        # As a user, I can create a DatedMeasure with only RQS,
        # it will launch a task
        self.check_create_case(self.basic_case)

    def test_create_with_global(self):
        # As a user, I can create a DatedMeasure with only RQS,
        # it will launch a task
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data, 'global_estimate': True}
        ))

    def test_create_with_data(self):
        # As a user, I can create a DatedMeasure with all fields,
        # no task will be launched
        dm: DatedMeasure = DatedMeasure.objects.create(
            request_query_snapshot=self.user1_req1_snap1,
            owner=self.user1,
            measure=1,
            fhir_datetime=timezone.now()
        )
        self.check_create_case(self.basic_case.clone(
            data={
                **self.basic_data,
                'fhir_group_id': random_str(5),
                'dated_measure': dm.uuid,
                'dated_measure_global': dm.uuid,
            },
            mock_task_called=False,
        ))

    def test_create_with_unread_fields(self):
        # As a user, I can create a dm
        self.check_create_case(self.basic_case.clone(
            data={**self.basic_data,
                  'create_task_id': random_str(5),
                  'request_job_fail_msg': random_str(5),
                  'request_job_id': random_str(5),
                  'request_job_duration': '1',
                  'created_at': timezone.now() + timedelta(hours=1),
                  'modified_at': timezone.now() + timedelta(hours=1),
                  'deleted': timezone.now() + timedelta(hours=1)},
        ))

    def test_error_create_missing_field(self):
        # As a user, I cannot create a dm if some field is missing
        cases = (self.basic_err_case.clone(
            data={**self.basic_data, k: None},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ) for k in ['request_query_snapshot'])
        [self.check_create_case(case) for case in cases]

    def test_error_create_with_other_owner(self):
        # As a user, I cannot create a cohort providing another user as owner
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data, 'owner': self.user2.pk},
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
        ))

    def test_create_from_rqs(self):
        # As a user, I can create a RQS specifying a previous snapshot
        # using nestedViewSet
        self.check_create_case(self.basic_case.clone(
            data={'name': self.test_name},
        ), NestedCohortResultViewSet.as_view({'post': 'create'}),
            request_query_snapshot=self.user1_req1_snap1.pk)

    def test_error_create_on_rqs_not_owned(self):
        # As a user, I cannot create a dm on a Rqs I don't own
        self.check_create_case(self.basic_err_case.clone(
            data={**self.basic_data,
                  'request_query_snapshot': self.user2_req1_snap1.pk},
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        ))


class CohortsDeleteTests(CohortsTests):
    # def check_delete_case(self, case: DMDeleteCase):
    #     obj = self.model_objects.create(**case.data_to_delete)
    #
    #     if case.with_cohort:
    #         CohortResult.objects.create(
    #             dated_measure=obj,
    #             request_query_snapshot=obj.request_query_snapshot,
    #             owner=obj.owner,
    #         )
    #
    #     request = self.factory.delete(self.objects_url)
    #     force_authenticate(request, case.user)
    #     response = self.__class__.delete_view(
    #         request, **{self.model._meta.pk.name: obj.pk}
    #     )
    #     response.render()
    #
    #     self.assertEqual(
    #         response.status_code, case.status,
    #         msg=(f"{case.description}"
    #              + (f" -> {prettify_json(response.content)}"
    #                 if response.content else "")),
    #     )
    #
    #     obj = self.model.all_objects.filter(pk=obj.pk).first()
    #
    #     if case.success:
    #         self.check_is_deleted(obj)
    #     else:
    #         self.assertIsNotNone(obj)
    #         self.assertIsNone(obj.deleted)
    #         obj.delete()
    #
    def setUp(self):
        super(CohortsDeleteTests, self).setUp()
        self.user1_req1_snap1_dm: DatedMeasure = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            measure=1,
            fhir_datetime=timezone.now(),
        )
        self.basic_data = dict(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            dated_measure=self.user1_req1_snap1_dm,
            create_task_id="test",
            created_at=timezone.now(),
            modified_at=timezone.now(),
            request_job_id="test",
            request_job_status=JobStatus.pending.name,
            request_job_fail_msg="test",
            request_job_duration="1s",
        )

    def test_delete_owned_dm_without_cohort(self):
        # As a user, I can delete a cohort result I owned
        self.check_delete_case(DMDeleteCase(
            data_to_delete=self.basic_data,
            status=status.HTTP_204_NO_CONTENT,
            success=True,
            user=self.user1,
        ))

    def test_error_delete_not_owned(self):
        # As a user, I cannot delete a cohort result linekd to a CohortResult
        self.check_delete_case(DMDeleteCase(
            data_to_delete=self.basic_data,
            status=status.HTTP_404_NOT_FOUND,
            success=False,
            user=self.user2,
        ))


class CohortsUpdateTests(CohortsTests):
    def setUp(self):
        super(CohortsUpdateTests, self).setUp()
        self.user1_req1_snap1_dm: DatedMeasure = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            measure=1,
            fhir_datetime=timezone.now(),
        )
        self.basic_data = dict(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            dated_measure=self.user1_req1_snap1_dm,
            create_task_id="test",
            created_at=timezone.now(),
            modified_at=timezone.now(),
            request_job_id="test",
            request_job_status=JobStatus.pending.name,
            request_job_fail_msg="test",
            request_job_duration="1s",
        )
        self.basic_case = PatchCase(
            initial_data=self.basic_data,
            status=status.HTTP_200_OK,
            success=True,
            user=self.user1,
            data_to_update={},
        )
        self.basic_err_case = self.basic_case.clone(
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
        )

    def test_update_cohort_as_owner(self):
        # As a user, I can patch a CR I own
        self.check_patch_case(self.basic_case.clone(
            data_to_update=dict(
                name="new_name",
                description="new_desc",
                # read_only
                create_task_id="test_task_id",
                request_job_id="test_job_id",
                request_job_status=JobStatus.finished,
                request_job_fail_msg="test_fail_msg",
                request_job_duration=1001,
                created_at=timezone.now() + timedelta(hours=1),
                modified_at=timezone.now() + timedelta(hours=1),
                deleted=timezone.now() + timedelta(hours=1),
            )
        ))

    def test_error_update_cohort_as_not_owner(self):
        # As a user, I cannot update another user's cohort result
        self.check_patch_case(self.basic_err_case.clone(
            data_to_update=dict(
                name="new_name",
            ),
            user=self.user2,
            status=status.HTTP_404_NOT_FOUND,
        ))

    def test_error_update_cohort_forbidden_fields(self):
        user1_req1_snap1_dm2: DatedMeasure = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            measure=2,
            fhir_datetime=timezone.now(),
        )

        cases = [self.basic_err_case.clone(
            data_to_update={k: v},
        ) for (k, v) in dict(
            owner=self.user2.pk,
            request_query_snapshot=self.user1_req1_branch1_snap2.pk,
            dated_measure=user1_req1_snap1_dm2.pk
        ).items()]
        [self.check_patch_case(case) for case in cases]


# TASKS


class TasksTests(DatedMeasuresTests):
    def setUp(self):
        super(TasksTests, self).setUp()
        self.test_count = 102
        self.test_datetime = timezone.now().replace(tzinfo=timezone.utc)
        self.test_job_id = "job_id"
        self.test_task_id = "task_id"
        self.test_job_duration = 1000
        self.test_job_status_finished = JobStatus.finished

        self.user1_req1_snap1_empty_dm = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            count_task_id=self.test_task_id,
            request_job_status=JobStatus.pending
        )
        self.user1_req1_snap1_empty_global_dm = DatedMeasure.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            count_task_id=self.test_task_id,
            request_job_status=JobStatus.pending,
            mode=GLOBAL_DM_MODE,
        )

        self.user1_req1_snap1_empty_cohort = CohortResult.objects.create(
            owner=self.user1,
            request_query_snapshot=self.user1_req1_snap1,
            name="My empty cohort",
            description="so empty",
            create_task_id="task_id",
            request_job_status=JobStatus.pending,
            dated_measure=self.user1_req1_snap1_empty_dm
        )

        self.basic_count_data_response = dict(
            count=self.test_count,
            count_max=self.test_count,
            count_min=self.test_count,
            count_male=self.test_count,
            count_alive=self.test_count,
            count_female=self.test_count,
            count_unknown=self.test_count,
            count_deceased=self.test_count,
            fhir_datetime=self.test_datetime,
            fhir_job_id=self.test_job_id,
            job_duration=self.test_job_duration,
            success=True,
            fhir_job_status=self.test_job_status_finished
        )
        self.basic_create_data_response = {
            **self.basic_count_data_response,
            'group_id': self.test_job_id,
        }

    @mock.patch('cohort.tasks.fhir_api')
    def test_get_count_task(self, mock_fhir_api: MagicMock):
        mock_fhir_api.post_count_cohort.return_value = FhirCountResponse(
            **self.basic_count_data_response
        )
        get_count_task({}, "{}", self.user1_req1_snap1_empty_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            pk=self.user1_req1_snap1_empty_dm.uuid,
            measure_min__isnull=True,
            measure_max__isnull=True,
            measure=self.test_count,
            measure_male=self.test_count,
            measure_unknown=self.test_count,
            measure_deceased=self.test_count,
            measure_alive=self.test_count,
            measure_female=self.test_count,
            fhir_datetime=self.test_datetime,
            request_job_duration=self.test_job_duration,
            request_job_status=self.test_job_status_finished,
            request_job_id=self.test_job_id,
            # count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.fhir_api')
    def test_get_count_global_task(self, mock_fhir_api):
        mock_fhir_api.post_count_cohort.return_value = FhirCountResponse(
            **self.basic_count_data_response
        )
        get_count_task({}, "{}", self.user1_req1_snap1_empty_global_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            pk=self.user1_req1_snap1_empty_global_dm.uuid,
            measure__isnull=True,
            measure_min=self.test_count,
            measure_max=self.test_count,
            measure_male__isnull=True,
            measure_unknown__isnull=True,
            measure_deceased__isnull=True,
            measure_alive__isnull=True,
            measure_female__isnull=True,
            fhir_datetime=self.test_datetime,
            request_job_duration=self.test_job_duration,
            request_job_status=self.test_job_status_finished,
            request_job_id=self.test_job_id,
            # count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()
        self.assertIsNotNone(new_dm)

    @mock.patch('cohort.tasks.fhir_api')
    def test_failed_get_count_task(self, mock_fhir_api):
        test_err_msg = "Error"
        job_status = JobStatus.failed

        mock_fhir_api.post_count_cohort.return_value = FhirCountResponse(
            fhir_job_id=self.test_job_id,
            job_duration=self.test_job_duration,
            fhir_job_status=job_status,
            success=False,
            err_msg=test_err_msg,
        )

        get_count_task({}, "{}", self.user1_req1_snap1_empty_dm.uuid)

        new_dm = DatedMeasure.objects.filter(
            pk=self.user1_req1_snap1_empty_dm.uuid,
            measure__isnull=True,
            measure_min__isnull=True,
            measure_max__isnull=True,
            measure_male__isnull=True,
            measure_unknown__isnull=True,
            measure_deceased__isnull=True,
            measure_alive__isnull=True,
            measure_female__isnull=True,
            request_job_id=self.test_job_id,
            request_job_duration=self.test_job_duration,
            request_job_status=job_status,
            request_job_fail_msg=test_err_msg,
            # count_task_id=self.user1_req1_snap1_empty_dm.count_task_id
        ).first()

        # while calling Fhir API
        self.assertIsNotNone(new_dm)
        self.assertIsNone(new_dm.measure)
        self.assertIsNone(new_dm.fhir_datetime)

    @mock.patch('cohort.tasks.fhir_api')
    def test_create_cohort_task(self, mock_fhir_api):
        mock_fhir_api.post_create_cohort.return_value = FhirCohortResponse(
            **self.basic_create_data_response
        )
        create_cohort_task({}, "{}", self.user1_req1_snap1_empty_cohort.uuid)

        new_cr = CohortResult.objects.filter(
            pk=self.user1_req1_snap1_empty_cohort.pk,
            dated_measure=self.user1_req1_snap1_empty_dm,
            dated_measure__measure=self.test_count,
            dated_measure__measure_min__isnull=True,
            dated_measure__measure_max__isnull=True,
            dated_measure__measure_male=self.test_count,
            dated_measure__measure_unknown=self.test_count,
            dated_measure__measure_deceased=self.test_count,
            dated_measure__measure_alive=self.test_count,
            dated_measure__measure_female=self.test_count,

            dated_measure__fhir_datetime=self.test_datetime,
            dated_measure__request_job_duration=self.test_job_duration,
            dated_measure__request_job_status=self.test_job_status_finished,
            dated_measure__request_job_id=self.test_job_id,
            # dated_measure__count_task_id=(self.user1_req1_snap1_empty_dm
            #                               .count_task_id),

            request_job_status=self.test_job_status_finished,
            fhir_group_id=self.test_job_id,
            request_job_id=self.test_job_id,
            request_job_duration=self.test_job_duration,
            # create_task_id=self.user1_req1_snap1_empty_cohort.create_task_id
        ).first()
        self.assertIsNotNone(new_cr)

    @mock.patch('cohort.tasks.fhir_api')
    def test_failed_create_cohort_task(self, mock_fhir_api):
        test_err_msg = "Error"
        job_status = JobStatus.failed

        mock_fhir_api.post_create_cohort.return_value = FhirCohortResponse(
            fhir_job_id=self.test_job_id,
            job_duration=self.test_job_duration,
            fhir_job_status=job_status,
            success=False,
            err_msg=test_err_msg,
        )

        create_cohort_task({}, "{}", self.user1_req1_snap1_empty_cohort.uuid)

        new_cr = CohortResult.objects.filter(
            pk=self.user1_req1_snap1_empty_cohort.pk,
            dated_measure=self.user1_req1_snap1_empty_dm,
            dated_measure__measure__isnull=True,
            dated_measure__measure_min__isnull=True,
            dated_measure__measure_max__isnull=True,
            dated_measure__measure_male__isnull=True,
            dated_measure__measure_unknown__isnull=True,
            dated_measure__measure_deceased__isnull=True,
            dated_measure__measure_alive__isnull=True,
            dated_measure__measure_female__isnull=True,
            dated_measure__fhir_datetime__isnull=True,
            dated_measure__request_job_duration=self.test_job_duration,
            dated_measure__request_job_status=JobStatus.failed.value,
            dated_measure__request_job_fail_msg=test_err_msg,
            dated_measure__request_job_id=self.test_job_id,
            # dated_measure__count_task_id=(self.user1_req1_snap1_empty_dm
            #                               .count_task_id),
            request_job_status=JobStatus.failed.value,
            request_job_fail_msg=test_err_msg,
            fhir_group_id="",
            request_job_id=self.test_job_id,
            request_job_duration=self.test_job_duration,
            # create_task_id=self.user1_req1_snap1_empty_cohort.create_task_id
        ).first()
        # TODO: I could not find how to test that intermediate state of
        #  request_job_status is set to 'started'
        # while calling Fhir API
        self.assertIsNotNone(new_cr)
