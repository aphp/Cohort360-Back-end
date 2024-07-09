from django_celery_beat.models import CrontabSchedule, PeriodicTask

from cohort.models import RequestRefreshSchedule, DatedMeasure, RequestQuerySnapshot
from cohort.services.base_service import CommonService
from cohort.services.utils import RefreshFrequency, get_authorization_header_for_refresh_request
from cohort.tasks import refresh_count_request

FREQUENCIES = {RefreshFrequency.DAILY.value: '*',
               RefreshFrequency.EVER_OTHER_DAY.value: '*/2',
               RefreshFrequency.WEEKLY.value: '*/7'
               }


class RequestsService(CommonService):
    job_type = "count"

    def create_refresh_schedule(self, refresh_schedule: RequestRefreshSchedule) -> None:
        crontab_schedule = self.create_crontab_schedule(refresh_schedule)
        count_request = refresh_schedule.request
        last_rqs = count_request.query_snapshots.last()
        dm_id = self.copy_dated_measure(dm=last_rqs.dated_measures.last(), rqs=last_rqs).uuid
        json_query = last_rqs.json_query
        auth_headers = get_authorization_header_for_refresh_request()
        task_args = [dm_id, json_query, auth_headers, self.operator_cls, refresh_schedule.uuid]
        task = f"{refresh_count_request.__module__}.{refresh_count_request.__name__}"
        PeriodicTask.objects.create(name=count_request.uuid,
                                    crontab=crontab_schedule,
                                    task=task,
                                    args=str(task_args))

    def update_refresh_schedule(self, refresh_schedule: RequestRefreshSchedule) -> None:
        periodic_task = PeriodicTask.objects.get(name=refresh_schedule.request.uuid)
        periodic_task.crontab = self.create_crontab_schedule(refresh_schedule)
        periodic_task.save()

    @staticmethod
    def create_crontab_schedule(refresh_schedule: RequestRefreshSchedule):
        return CrontabSchedule.objects.create(minute=refresh_schedule.refresh_time.minute,
                                              hour=refresh_schedule.refresh_time.hour,
                                              day_of_week='*',
                                              day_of_month=FREQUENCIES.get(refresh_schedule.refresh_frequency, '*'),
                                              month_of_year='*')

    @staticmethod
    def copy_dated_measure(dm: DatedMeasure, rqs: RequestQuerySnapshot) -> DatedMeasure:
        return DatedMeasure.objects.create(mode=dm.mode,
                                           owner=dm.owner,
                                           request_query_snapshot=rqs,
                                           measure=dm.measure)


requests_service = RequestsService()
