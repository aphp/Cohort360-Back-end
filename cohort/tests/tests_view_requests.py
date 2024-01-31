import random
from datetime import timedelta
from typing import List

from django.utils import timezone
from rest_framework import status

from admin_cohort.models import User
from admin_cohort.tests.tests_tools import CaseRetrieveFilter, random_str, ListCase, RetrieveCase, CreateCase, DeleteCase, \
    PatchCase, RequestCase
from cohort.models import Request, Folder
from cohort.models.request import REQUEST_DATA_TYPES, PATIENT_DATA_TYPE
from cohort.tests.cohort_app_tests import CohortAppTests
from cohort.tests.tests_view_folders import FolderCaseRetrieveFilter
from cohort.views import RequestViewSet, NestedRequestViewSet


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


class RequestCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str = "", **kwargs):
        self.name = name
        super(RequestCaseRetrieveFilter, self).__init__(**kwargs)


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
                data_type_of_query=random.choice(REQUEST_DATA_TYPES)[0],
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
                params=dict(data_type_of_query=REQUEST_DATA_TYPES[0][0]),
                to_find=[f for f in user1_requests
                         if (f.data_type_of_query ==
                             REQUEST_DATA_TYPES[0][0])],
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

        self.check_get_paged_list_case(ListCase(status=status.HTTP_200_OK,
                                                success=True,
                                                user=self.user1,
                                                to_find=list(folder.requests.all())),
                                       other_view=NestedRequestViewSet.as_view({'get': 'list'}),
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
            data_type_of_query=PATIENT_DATA_TYPE,
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
            data_type_of_query=PATIENT_DATA_TYPE,
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
            data_type_of_query=PATIENT_DATA_TYPE,
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
                data_type_of_query=REQUEST_DATA_TYPES[1][0],
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
