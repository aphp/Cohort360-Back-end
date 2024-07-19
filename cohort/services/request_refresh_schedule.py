from django.utils.timezone import now
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from cohort.models import RequestRefreshSchedule, DatedMeasure, RequestQuerySnapshot
from cohort.services.base_service import CommonService, load_operator
from cohort.services.utils import RefreshFrequency, get_authorization_header
from cohort.tasks import refresh_count_request, send_email_count_request_refreshed

FREQUENCIES = {RefreshFrequency.DAILY.value: '*',
               RefreshFrequency.EVERY_OTHER_DAY.value: '*/2',
               RefreshFrequency.WEEKLY.value: '*/7'
               }


class RequestRefreshScheduleService(CommonService):
    job_type = "count"

    def create_refresh_schedule(self, http_request, refresh_schedule: RequestRefreshSchedule) -> None:
        crontab_schedule = self.create_crontab_schedule(refresh_schedule)
        req = refresh_schedule.request
        last_rqs = req.query_snapshots.last()
        dm_id = DatedMeasure.objects.create(owner=last_rqs.owner,
                                            request_query_snapshot=last_rqs).uuid
        self.translate_snapshot_query(rqs=last_rqs,
                                      dm_id=dm_id,
                                      auth_headers=get_authorization_header(http_request))
        task_args = [dm_id, last_rqs.translated_query, req.uuid, self.operator_cls]
        task = f"{refresh_count_request.__module__}.{refresh_count_request.__name__}"
        PeriodicTask.objects.create(name=req.uuid,
                                    crontab=crontab_schedule,
                                    task=task,
                                    args=str(task_args))

    def translate_snapshot_query(self, rqs: RequestQuerySnapshot, dm_id: str, auth_headers: dict) -> None:
        cohort_counter = load_operator(self.operator_cls)
        rqs.translated_query = cohort_counter.translate_query(dm_id=dm_id,
                                                              json_query=rqs.serialized_query,
                                                              auth_headers=auth_headers)
        rqs.save()

    def reset_schedule_crontab(self, refresh_schedule: RequestRefreshSchedule) -> None:
        periodic_task = PeriodicTask.objects.get(name=refresh_schedule.request.uuid)
        periodic_task.crontab = self.create_crontab_schedule(refresh_schedule)
        periodic_task.save()

    @staticmethod
    def update_refresh_scheduler(dm: DatedMeasure) -> None:
        request = dm.request_query_snapshot.request
        refresh_schedule = request.refresh_schedules.all()
        if refresh_schedule:
            assert refresh_schedule.count() == 1, "Multiple refresh schedules found"
            refresh_schedule.update(last_refresh=now(),
                                    last_refresh_succeeded=True,
                                    last_refresh_count=dm.measure,
                                    last_refresh_error_msg=dm.request_job_fail_msg)
            refresh_schedule = refresh_schedule.last()
            if refresh_schedule.notify_owner:
                send_email_count_request_refreshed.s(request_id=refresh_schedule.request_id)\
                                                  .apply_async()

    @staticmethod
    def create_crontab_schedule(refresh_schedule: RequestRefreshSchedule):
        return CrontabSchedule.objects.create(minute=refresh_schedule.refresh_time.minute,
                                              hour=refresh_schedule.refresh_time.hour,
                                              day_of_week='*',
                                              day_of_month=FREQUENCIES.get(refresh_schedule.refresh_frequency, '*'),
                                              month_of_year='*')


requests_refresher_service = RequestRefreshScheduleService()
