from typing import List

from rest_framework.exceptions import ValidationError

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from accesses.services.shared import DataRight
from admin_cohort.models import User
from cohort.models import CohortResult
from exports.enums import ExportType


class RightsChecker:
    right_read_nomi = "right_read_patient_nominative"
    right_read_pseudo = "right_read_patient_pseudonymized"
    right_csv_nomi = "right_export_csv_nominative"
    right_csv_pseudo = "right_export_csv_pseudonymized"
    right_jupyter_nomi = "right_export_jupyter_nominative"
    right_jupyter_pseudo = "right_export_jupyter_pseudonymized"

    def check_owner_rights(self, owner: User, output_format:  str, nominative: bool, source_cohorts_ids: List[str]) -> None:
        cohort_ids = []
        for cohort in CohortResult.objects.filter(pk__in=source_cohorts_ids):
            cohort_ids.extend(cohort.request_query_snapshot.perimeters_ids)
        perimeters_ids = Perimeter.objects.filter(cohort_id__in=cohort_ids).values_list('id', flat=True)
        data_permissions = accesses_service.get_data_reading_rights(user=owner,
                                                                    target_perimeters_ids=','.join(map(str, perimeters_ids)))
        self._check_rights(data_permissions=data_permissions, required_right=nominative and self.right_read_nomi or self.right_read_pseudo)
        if output_format == ExportType.CSV:
            required_right = nominative and self.right_csv_nomi or self.right_csv_pseudo
        else:
            required_right = nominative and self.right_jupyter_nomi or self.right_jupyter_pseudo
        self._check_rights(data_permissions=data_permissions, required_right=required_right)

    @staticmethod
    def _check_rights(data_permissions: List[DataRight], required_right: str) -> None:
        wrong_perimeters = [p.perimeter_id for p in data_permissions if not getattr(p, required_right, False)]
        if wrong_perimeters:
            raise ValidationError(f"The user is missing `{required_right}` on the following perimeters: {wrong_perimeters}.")


rights_checker = RightsChecker()
