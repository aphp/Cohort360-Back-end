from django.db.models import QuerySet

from accesses.models import Role, Perimeter
from accesses.services.access import accesses_service
from admin_cohort.models import User


class RolesService:

    @staticmethod
    def role_has_inconsistent_rights(data: dict) -> bool:
        return data.get("right_read_patient_pseudonymized") and \
               not data.get("right_read_patient_nominative") and \
               (data.get("right_export_csv_nominative") or data.get("right_export_jupyter_nominative"))

    @staticmethod
    def get_assignable_roles(user: User, perimeter_id: str) -> QuerySet:
        perimeter = Perimeter.objects.get(id=perimeter_id)
        assignable_roles_ids = [role.id for role in Role.objects.all()
                                if accesses_service.can_user_manage_role_on_perimeter(user=user,
                                                                                      target_role=role,
                                                                                      target_perimeter=perimeter)]
        return Role.objects.filter(id__in=assignable_roles_ids)


roles_service = RolesService()
