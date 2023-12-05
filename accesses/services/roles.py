from django.db.models import QuerySet

from accesses.models import Role, Perimeter
from accesses.services.access import accesses_service
from admin_cohort.models import User


class RolesService:

    @staticmethod
    def can_manage_accesses(role: Role):
        return any((role.right_full_admin,
                    role.right_manage_admin_accesses_same_level,
                    role.right_manage_admin_accesses_inferior_levels,
                    role.right_manage_data_accesses_same_level,
                    role.right_manage_data_accesses_inferior_levels,
                    role.right_manage_export_jupyter_accesses,
                    role.right_manage_export_csv_accesses))

    def can_read_accesses(self, role: Role):
        return self.can_manage_accesses(role=role) \
            or any((role.right_read_admin_accesses_same_level,
                    role.right_read_admin_accesses_inferior_levels,
                    role.right_read_data_accesses_same_level,
                    role.right_read_data_accesses_inferior_levels,
                    role.right_read_accesses_above_levels))

    @staticmethod
    def role_has_inconsistent_rights(data: dict) -> bool:
        allow_read_data_pseudo_and_export_nomi = not data.get("right_read_patient_nominative") and \
                                                 data.get("right_read_patient_pseudonymized") and \
                                                 (data.get("right_export_csv_nominative") or
                                                  data.get("right_export_jupyter_nominative"))
        allow_manage_or_read_accesses_but_not_users = any((data.get("right_manage_data_accesses_same_level"),
                                                           data.get("right_read_data_accesses_same_level"),
                                                           data.get("right_manage_data_accesses_inferior_levels"),
                                                           data.get("right_read_data_accesses_inferior_levels"),
                                                           data.get("right_manage_admin_accesses_same_level"),
                                                           data.get("right_read_admin_accesses_same_level"),
                                                           data.get("right_manage_admin_accesses_inferior_levels"),
                                                           data.get("right_read_admin_accesses_inferior_levels"),
                                                           data.get("right_manage_export_csv_accesses"),
                                                           data.get("right_manage_export_jupyter_accesses"),
                                                           data.get("right_read_accesses_above_levels")))
        return allow_read_data_pseudo_and_export_nomi or allow_manage_or_read_accesses_but_not_users

    @staticmethod
    def get_assignable_roles(user: User, perimeter_id: str) -> QuerySet:
        perimeter = Perimeter.objects.get(id=perimeter_id)
        assignable_roles_ids = [role.id for role in Role.objects.all()
                                if accesses_service.can_user_create_access(user=user, access_data=dict(role=role, perimeter=perimeter))]
        return Role.objects.filter(id__in=assignable_roles_ids)


roles_service = RolesService()
