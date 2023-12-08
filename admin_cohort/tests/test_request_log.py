from rest_framework import status
from rest_framework.test import force_authenticate
from rest_framework_tracking.models import APIRequestLog

from accesses.models import Access, Perimeter, Role
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.tools.tests_tools import BaseTests, new_user_and_profile
from admin_cohort.views import RequestLogViewSet

REQUEST_LOGS_URL = "/logs"


def create_sample_logs_data(user) -> None:
    APIRequestLog.objects.create(requested_at="2023-11-11 11:00:00",
                                 response_ms="65",
                                 path="/cohort/folders/",
                                 remote_addr="10.172.142.121",
                                 host="django-prod-ext-k8s.eds.aphp.fr",
                                 method="POST",
                                 query_params="{'uuid': '', 'name': 'individualisation'}",
                                 data='{"uuid": "", "name": "individualisation"}',
                                 response='{"uuid": "da3837ed-35fd-450a-8404-202de01fb4c1", "owner": "4024023", "requests": [], "deleted": null,'
                                          '"deleted_by_cascade": false, "created_at": "2023-11-22T17:10:58.737893Z", "modified_at": '
                                          '"2023-11-22T17:10:58.737899Z", "name": "individualisation"}',
                                 status_code="201",
                                 user_id=user.pk,
                                 view="cohort.views.folder.FolderViewSet",
                                 view_method="create",
                                 username_persistent=user.pk)


class RequestLogTests(BaseTests):
    def setUp(self):
        super(RequestLogTests, self).setUp()
        self.aphp = Perimeter.objects.create(**dict(local_id=1,
                                                    name="APHP",
                                                    parent=None,
                                                    type_source_value=PERIMETERS_TYPES[0],
                                                    source_value="APHP"))
        self.user, self.profile = new_user_and_profile(firstname="User", lastname="USERSON", email="u.userson@aphp.fr")
        self.user_role = Role.objects.create(**dict([(f, True) for f in self.all_rights]), name='FullAdmin')
        self.user_access = Access.objects.create(perimeter=self.aphp,
                                                 role=self.user_role,
                                                 profile=self.profile)
        create_sample_logs_data(user=self.user)

    def test_list_request_logs(self):
        request = self.factory.get(REQUEST_LOGS_URL)
        force_authenticate(request, self.user)
        response = RequestLogViewSet.as_view({'get': 'list'})(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
