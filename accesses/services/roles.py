from typing import Tuple

from django.db.models import QuerySet

from accesses.models import Role, Perimeter
from accesses.services.access import accesses_service
from admin_cohort.models import User


class RolesService:

    def check_role_validity(self, data: dict) -> Tuple[bool, str]:
        error_msg = ""
        role = self.check_for_existing_role(data=data)
        if role:
            error_msg = f"Un rôle avec les mêmes droits est déjà configuré: <{role.name}>"
        if self.role_has_inconstant_rights(rights=data):
            error_msg = "Les droits activés sur le rôle ne sont pas cohérents"
        return bool(error_msg), error_msg

    @staticmethod
    def check_for_existing_role(data: dict) -> Role:
        data.pop("name", None)
        return Role.objects.filter(**data).first()

    @staticmethod
    def role_has_inconstant_rights(rights: dict) -> bool:
        return rights.get("right_read_patient_pseudonymized") and \
               (rights.get("right_export_csv_nominative")
                or rights.get("right_export_jupyter_nominative"))

    @staticmethod
    def get_assignable_roles(user: User, perimeter_id: str) -> QuerySet:
        perimeter = Perimeter.objects.get(id=perimeter_id)
        assignable_roles_ids = [role.id for role in Role.objects.all()
                                if accesses_service.can_user_manage_role_on_perimeter(user=user,
                                                                                      target_role=role,
                                                                                      target_perimeter=perimeter)]
        return Role.objects.filter(id__in=assignable_roles_ids)


roles_service = RolesService()
