import datetime
from unittest import mock

from django.db import IntegrityError
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from rest_framework import status

from admin_cohort.tests.tests_tools import CreateCase, CaseRetrieveFilter, PatchCase
from cohort.models import RequestRefreshSchedule, Folder, Request, RequestQuerySnapshot, DatedMeasure
from cohort.services.request_refresh_schedule import RequestRefreshScheduleService, FREQUENCIES, requests_refresher_service
from cohort.services.utils import RefreshFrequency
from cohort.tests.cohort_app_tests import CohortAppTests
from cohort.views import RequestRefreshScheduleViewSet


class RequestRefreshScheduleRetrieveFilter(CaseRetrieveFilter):

    def __init__(self, request_snapshot_id: str, exclude: dict = None):
        self.request_snapshot_id = request_snapshot_id
        super().__init__(exclude=exclude)


class RequestRefreshScheduleViewTests(CohortAppTests):
    objects_url = "/refresh-schedules/"
    retrieve_view = RequestRefreshScheduleViewSet.as_view({'get': 'retrieve'})
    list_view = RequestRefreshScheduleViewSet.as_view({'get': 'list'})
    create_view = RequestRefreshScheduleViewSet.as_view({'post': 'create'})
    delete_view = RequestRefreshScheduleViewSet.as_view({'delete': 'destroy'})
    update_view = RequestRefreshScheduleViewSet.as_view({'patch': 'partial_update'})
    model = RequestRefreshSchedule
    model_objects = RequestRefreshSchedule.objects

    def setUp(self):
        super().setUp()
        self.folder = Folder.objects.create(owner=self.user1, name="f1")
        self.request = Request.objects.create(owner=self.user1,
                                              name="Request 1",
                                              description="Request 1",
                                              parent_folder=self.folder)
        self.rqs = RequestQuerySnapshot.objects.create(owner=self.user1,
                                                       request=self.request,
                                                       serialized_query='{}')
        self.dm = DatedMeasure.objects.create(owner=self.user1,
                                              request_query_snapshot=self.rqs)

        self.basic_data = {"request_snapshot_id": self.rqs.uuid,
                           "owner_id": self.user1.username,
                           "refresh_time": "11:45:00",
                           "refresh_frequency": RefreshFrequency.WEEKLY.value,
                           }

    def test_unique_refresh_schedule_not_deleted(self):
        first_schedule = RequestRefreshSchedule.objects.create(**self.basic_data)
        self.assertIsNotNone(first_schedule)
        with self.assertRaises(IntegrityError):
            RequestRefreshSchedule.objects.create(**{**self.basic_data,
                                                     "refresh_time": "12:00:00"})

    def test_duplicate_refresh_schedule_deleted(self):
        first_schedule = RequestRefreshSchedule.objects.create(**self.basic_data)
        self.assertIsNotNone(first_schedule)
        first_schedule.delete()
        self.assertIsNotNone(first_schedule.deleted)
        try:
            RequestRefreshSchedule.objects.create(**{**self.basic_data})
        except IntegrityError:
            self.fail("Must be able to create a new Refresh Schedule object")

    @mock.patch('cohort.services.request_refresh_schedule.get_authorization_header')
    @mock.patch.object(RequestRefreshScheduleService, 'translate_snapshot_query')
    def test_successfully_creating_refresh_schedule(self, mock_translate_query, mock_get_auth_headers):
        mock_translate_query.return_value = None
        mock_get_auth_headers.return_value = None
        request_snapshot_id = self.basic_data["request_snapshot_id"]
        case = CreateCase(data=self.basic_data,
                          retrieve_filter=RequestRefreshScheduleRetrieveFilter(request_snapshot_id=request_snapshot_id),
                          user=self.user1,
                          status=status.HTTP_201_CREATED,
                          success=True)
        self.check_create_case(case)
        mock_translate_query.assert_called_once()
        mock_get_auth_headers.assert_called_once()
        periodic_task = PeriodicTask.objects.get(name=request_snapshot_id)
        self.assertIsNotNone(periodic_task)
        self.assertIsNotNone(periodic_task.crontab)

    def test_successfully_patch_refresh_schedule(self):
        request_snapshot_id = self.basic_data["request_snapshot_id"]
        initial_crontab = CrontabSchedule.objects.create(minute="10",
                                                         hour="12",
                                                         day_of_week='*',
                                                         day_of_month="*/7",   # weekly
                                                         month_of_year='*')
        PeriodicTask.objects.create(name=request_snapshot_id,
                                    crontab=initial_crontab)
        data_to_update = {"refresh_time": datetime.time(hour=9, minute=45, second=0),
                          "refresh_frequency": RefreshFrequency.EVERY_OTHER_DAY.value
                          }
        case = PatchCase(initial_data=self.basic_data,
                         data_to_update=data_to_update,
                         user=self.user1,
                         status=status.HTTP_200_OK,
                         success=True)
        resp_data = self.check_patch_case(case=case, return_response_data=True)
        self.assertEqual(resp_data.get("refresh_time"),
                         data_to_update["refresh_time"].strftime(format="%H:%M:%S"))
        self.assertEqual(resp_data.get("refresh_frequency"), data_to_update["refresh_frequency"])
        updated_crontab = PeriodicTask.objects.get(name=request_snapshot_id).crontab
        self.assertEqual(f"{int(updated_crontab.hour) >=10 and updated_crontab.hour or '0'+updated_crontab.hour}:{updated_crontab.minute}:00",
                         data_to_update["refresh_time"].strftime(format="%H:%M:%S"))
        self.assertEqual(updated_crontab.day_of_month, FREQUENCIES.get(data_to_update["refresh_frequency"], '*'))

    @mock.patch('cohort.services.request_refresh_schedule.send_email_count_request_refreshed.apply_async')
    def test_refresh_scheduler_updated(self, mock_send_email):
        mock_send_email.return_value = None
        refresh_schedule = RequestRefreshSchedule.objects.create(**self.basic_data, notify_owner=True)
        self.assertIsNone(refresh_schedule.last_refresh)
        self.assertIsNone(refresh_schedule.last_refresh_succeeded)
        self.dm.measure = 700
        self.dm.save()
        requests_refresher_service.update_refresh_scheduler(dm=self.dm)
        refresh_schedule.refresh_from_db()
        self.assertTrue(refresh_schedule.last_refresh_succeeded)
        self.assertIsNotNone(refresh_schedule.last_refresh)
        self.assertEqual(refresh_schedule.last_refresh_count, self.dm.measure)
        mock_send_email.assert_called_once()
