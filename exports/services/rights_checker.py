from typing import List

from rest_framework.exceptions import ValidationError

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from accesses.services.shared import DataRight
from admin_cohort.models import User
from cohort.models import CohortResult
from exports.types import ExportType


class RightsChecker:

    def check_owner_rights(self, owner: User, output_format:  str, nominative: bool, source_cohorts_ids: List[str]) -> None:
        cohort_ids = []
        for cohort in CohortResult.objects.filter(pk__in=source_cohorts_ids):
            cohort_ids.extend(cohort.request_query_snapshot.perimeters_ids)
        perimeters_ids = Perimeter.objects.filter(cohort_id__in=cohort_ids).values_list('id', flat=True)
        data_rights = accesses_service.get_data_reading_rights(user=owner,
                                                               target_perimeters_ids=','.join(map(str, perimeters_ids)))
        self.check_rights_on_perimeters(rights=data_rights,
                                        export_type=output_format,
                                        nominative=nominative)

    def check_rights_on_perimeters(self, rights: List[DataRight], export_type: str, nominative: bool) -> None:
        self.check_patient_data_read_rights(rights=rights, nominative=nominative)
        if export_type == ExportType.CSV:
            self.check_csv_export_rights(rights=rights, nominative=nominative)
        else:
            self.check_jupyter_export_rights(rights=rights, nominative=nominative)

    @staticmethod
    def check_patient_data_read_rights(rights: List[DataRight], nominative: bool) -> None:
        wrong_perimeters = [r.perimeter_id for r in rights
                            if (nominative and not r.right_read_patient_nominative)
                            or not (nominative or r.right_read_patient_pseudonymized)]
        if wrong_perimeters:
            raise ValidationError(f"The user has no  {nominative and 'nominative' or 'pseudonymized'} read right"
                                  f"on the following perimeters: {wrong_perimeters}.")

    @staticmethod
    def check_csv_export_rights(rights: List[DataRight], nominative: bool) -> None:
        wrong_perimeters = [r.perimeter_id for r in rights
                            if (nominative and not r.right_export_csv_nominative)
                            or not (nominative or r.right_export_csv_pseudonymized)]
        if wrong_perimeters:
            raise ValidationError(f"The user has no {nominative and 'nominative' or 'pseudonymized'} CSV export right"
                                  f"on the following perimeters: {wrong_perimeters}.")

    @staticmethod
    def check_jupyter_export_rights(rights: List[DataRight], nominative: bool) -> None:
        wrong_perimeters = [r.perimeter_id for r in rights
                            if (nominative and not r.right_export_jupyter_nominative)
                            or not (nominative or r.right_export_jupyter_pseudonymized)]
        if wrong_perimeters:
            raise ValidationError(f"The user has no {nominative and 'nominative' or 'pseudonymized'} Jupyter export right"
                                  f"on the following perimeters: {wrong_perimeters}.")


rights_checker = RightsChecker()
