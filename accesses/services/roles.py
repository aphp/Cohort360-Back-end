from django.db.models import QuerySet

from accesses.models import Role, Perimeter
from accesses.services.access import accesses_service
from admin_cohort.models import User


class RolesService:

    @staticmethod
    def check_existing_role(data: dict) -> Role:
        data.pop("name", None)
        return Role.objects.filter(**data).first()

    @staticmethod
    def check_role_validity(data: dict) -> str:
        """
        if given read data pseudo and export csv/jup nomi
        check other combinations
        """
        error_msg = ""
        data.pop("name", None)
        role = Role.objects.filter(**data).first()
        if role:
            error_msg = f"Un rôle avec les mêmes droits est déjà configuré: <{role.name}>"

        if data.get("right_read_patient_pseudonymized") and \
            (data.get("right_export_csv_nominative")
             or data.get("right_export_jupyter_nominative")):
            error_msg = "Les droits activés sur le rôle ne sont pas cohérents"
        return bool(error_msg) and error_msg

    @staticmethod
    def get_assignable_roles(user: User, perimeter_id: str) -> QuerySet:
        perimeter = Perimeter.objects.get(id=perimeter_id)
        assignable_roles_ids = [role.id for role in Role.objects.all()
                                if accesses_service.can_user_manage_role_on_perimeter(user=user, target_role=role, target_perimeter=perimeter)]
        return Role.objects.filter(id__in=assignable_roles_ids)


roles_service = RolesService()
