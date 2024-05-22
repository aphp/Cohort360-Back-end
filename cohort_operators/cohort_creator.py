from cohort.models import CohortResult
from cohort.services.misc import get_authorization_header
from .exceptions import ServerError
from .tasks import create_cohort_task


class CohortCreator:

    @staticmethod
    def launch_cohort_creation(cohort: CohortResult, request):
        try:
            create_cohort_task.s(auth_headers=get_authorization_header(request),
                                 json_query=cohort.request_query_snapshot.serialized_query,
                                 cohort_uuid=cohort.pk) \
                              .apply_async()

        except Exception as e:
            cohort.delete()
            raise ServerError("INTERNAL ERROR: Could not launch cohort creation") from e
