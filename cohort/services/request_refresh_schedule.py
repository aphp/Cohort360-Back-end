from django.utils.timezone import now
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from cohort.models import RequestRefreshSchedule, DatedMeasure
from cohort.services.base_service import CommonService
from cohort.services.utils import RefreshFrequency, get_authorization_header_for_refresh_request
from cohort.tasks import refresh_count_request

FREQUENCIES = {RefreshFrequency.DAILY.value: '*',
               RefreshFrequency.EVER_OTHER_DAY.value: '*/2',
               RefreshFrequency.WEEKLY.value: '*/7'
               }


class RequestRefreshScheduleService(CommonService):
    job_type = "count"

    def create_refresh_schedule(self, refresh_schedule: RequestRefreshSchedule) -> None:
        crontab_schedule = self.create_crontab_schedule(refresh_schedule)
        count_request = refresh_schedule.request
        last_rqs = count_request.query_snapshots.last()
        dm_id = DatedMeasure.objects.create(owner=last_rqs.owner,
                                            request_query_snapshot=last_rqs).uuid
        json_query = last_rqs.serialized_query
        auth_headers = get_authorization_header_for_refresh_request()
        task_args = [dm_id, json_query, auth_headers, self.operator_cls]
        task = f"{refresh_count_request.__module__}.{refresh_count_request.__name__}"
        PeriodicTask.objects.create(name=count_request.uuid,
                                    crontab=crontab_schedule,
                                    task=task,
                                    args=str(task_args))

    def reset_schedule_crontab(self, refresh_schedule: RequestRefreshSchedule) -> None:
        periodic_task = PeriodicTask.objects.get(name=refresh_schedule.request.uuid)
        periodic_task.crontab = self.create_crontab_schedule(refresh_schedule)
        periodic_task.save()

    @staticmethod
    def update_refreshing_metadata(dm: DatedMeasure) -> None:
        request = dm.request_query_snapshot.request
        refresh_schedule = request.refresh_schedules.all()
        if refresh_schedule:
            refresh_schedule.update(last_refresh=now(),
                                    last_refresh_succeeded=True,
                                    last_refresh_count=dm.measure,
                                    last_refresh_error_msg=dm.request_job_fail_msg)

    @staticmethod
    def create_crontab_schedule(refresh_schedule: RequestRefreshSchedule):
        return CrontabSchedule.objects.create(minute=refresh_schedule.refresh_time.minute,
                                              hour=refresh_schedule.refresh_time.hour,
                                              day_of_week='*',
                                              day_of_month=FREQUENCIES.get(refresh_schedule.refresh_frequency, '*'),
                                              month_of_year='*')


requests_refresher_service = RequestRefreshScheduleService()
