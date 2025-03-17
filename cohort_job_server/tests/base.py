from django.conf import settings
from django.test import TestCase

from accesses.models import Perimeter
from admin_cohort.tests.tests_tools import new_random_user
from cohort.models import Folder, Request, RequestQuerySnapshot, DatedMeasure


class BaseTest(TestCase):

    def setUp(self):
        super().setUp()
        self.perimeter = Perimeter.objects.create(name="Main Perimeter", level=1, cohort_id="1234")
        self.json_query = '{"sourcePopulation": {"caresiteCohortList": ["%s"]}}' % self.perimeter.cohort_id
        self.auth_headers = {'Authorization': 'Bearer XXXX', settings.AUTHORIZATION_METHOD_HEADER: settings.OIDC_AUTH_MODE}
        self.test_job_id = "some_job_id"
        self.test_err_msg = "Error Message"
        self.user = new_random_user()
        self.folder = Folder.objects.create(owner=self.user, name="folder")
        self.request = Request.objects.create(owner=self.user,
                                              name="Request 01",
                                              parent_folder=self.folder)
        self.snapshot = RequestQuerySnapshot.objects.create(owner=self.user,
                                                            request=self.request,
                                                            serialized_query=self.json_query)
        self.dm = DatedMeasure.objects.create(request_query_snapshot=self.snapshot, owner=self.user)
