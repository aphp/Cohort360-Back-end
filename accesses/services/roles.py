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
                    role.right_read_accesses_above_levels,
                    role.right_read_data_accesses_same_level,
                    role.right_read_data_accesses_inferior_levels))

    @staticmethod
    def role_has_inconsistent_rights(data: dict) -> bool:
        return data.get("right_read_patient_pseudonymized") and \
               not data.get("right_read_patient_nominative") and \
               (data.get("right_export_csv_nominative") or data.get("right_export_jupyter_nominative"))

    @staticmethod
    def get_assignable_roles(user: User, perimeter_id: str) -> QuerySet:
        """
        todo: - remove right_read_roles --> change Portail all users can see roles list
        todo: - remove right_manage_roles, only full_admin can manage them --> change Portail
        as an admin_accesses_manager (+ manage users), i should be able to assign the data_accesses_manager (+ manage users) role
        """
        perimeter = Perimeter.objects.get(id=perimeter_id)
        assignable_roles_ids = [role.id for role in Role.objects.all()
                                if accesses_service.can_user_create_access(user=user, access_data=dict(role=role, perimeter=perimeter))]
        return Role.objects.filter(id__in=assignable_roles_ids)

    @staticmethod
    def roles_comparator(role1: Role, role2: Role) -> int:
        if role1 > role2:
            return 1
        elif role1 < role2:
            return -1
        return 0


roles_service = RolesService()
