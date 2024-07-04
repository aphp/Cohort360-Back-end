import random
from datetime import timedelta
from typing import List

from django.utils import timezone
from rest_framework import status

from admin_cohort.tests.tests_tools import CaseRetrieveFilter, random_str, ListCase, RetrieveCase, CreateCase, DeleteCase, \
    PatchCase
from cohort.models import Folder
from cohort.tests.cohort_app_tests import CohortAppTests
from cohort.views import FolderViewSet


class FolderCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, name: str = "", **kwargs):
        self.name = name
        super(FolderCaseRetrieveFilter, self).__init__(**kwargs)


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
            Folder(name=random_str(10, random.random() > .5 and self.name_pattern),
                   owner=self.user1 if i % 2 else self.user2)
            for i in range(0, nb_base)])

        for f in self.folders[:nb_base]:
            self.folders += Folder.objects.bulk_create([
                Folder(name=random_str(10, random.random() > .5 and self.name_pattern),
                       owner=f.owner)])

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
        basic_case = ListCase(user=self.user1, success=True, status=status.HTTP_200_OK)
        user1_folders = [f for f in self.folders if f.owner == self.user1]
        cases = [basic_case.clone(params={"name": self.name_pattern},
                                  to_find=[f for f in user1_folders if self.name_pattern.lower() in f.name]),
                 ]
        [self.check_get_paged_list_case(case) for case in cases]


class FoldersCreateTests(FoldersTests):
    def setUp(self):
        super(FoldersCreateTests, self).setUp()
        self.test_name = "test"
        self.main_folder_name = "Main"
        self.user1_folder = Folder.objects.create(name=self.main_folder_name, owner=self.user1)
        self.user2_folder = Folder.objects.create(name=self.main_folder_name, owner=self.user2)

        self.basic_data = {"name": self.test_name}
        self.basic_case = CreateCase(success=True, status=status.HTTP_201_CREATED, user=self.user1,
                                     data=self.basic_data,
                                     retrieve_filter=FolderCaseRetrieveFilter(name=self.test_name, owner=self.user1))

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
        case = self.basic_case.clone(data={"owner": self.user2.pk,
                                           "name": self.test_name},
                                     success=False,
                                     status=status.HTTP_400_BAD_REQUEST,
                                     retrieve_filter=FolderCaseRetrieveFilter(name=self.test_name, owner=self.user2))
        self.check_create_case(case)


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
        initial_data = {"owner": self.user1,
                        "name": "test"
                        }
        data_to_update = {"name": "new_name",
                          # read_only
                          "created_at": timezone.now() + timedelta(hours=1),
                          "modified_at": timezone.now() + timedelta(hours=1),
                          "deleted": timezone.now() + timedelta(hours=1)
                          }
        case = self.basic_case.clone(initial_data=initial_data, data_to_update=data_to_update)
        self.check_patch_case(case)

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
