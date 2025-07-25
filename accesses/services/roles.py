from typing import List

from django.db import IntegrityError
from django.db.models import QuerySet

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from accesses.services.rights import all_rights
from admin_cohort.models import User

ROLES_HELP_TEXT = {"right_full_admin": "Super user",
                   "right_manage_users": "Gérer la liste des utilisateurs/profils",
                   "right_read_patient_nominative": "Lire les données patient sous forme nominatives sur son périmètre et ses sous-périmètres",
                   "right_read_patient_pseudonymized": "Lire les données patient sous forme pseudonymisée sur son périmètre et "
                                                    "ses sous-périmètres",
                   "right_search_patients_by_ipp": "Utiliser une liste d'IPP comme critère d'une requête Cohort.",
                   "right_search_opposed_patients": "Détermine le droit de chercher les patients opposés à l'utilisation "
                                                 "de leurs données pour la recherche",
                   "right_export_jupyter_nominative": "Exporter ses cohortes de patients sous forme nominative vers un environnement Jupyter.",
                   "right_export_jupyter_pseudonymized": "Exporter ses cohortes de patients sous forme pseudonymisée vers un environnement Jupyter.",
                   "right_export_csv_xlsx_nominative": "Demander à exporter ses cohortes de patients sous forme nominative en format CSV/Excel.",
                   "right_manage_datalabs": "Gérer les environnements de travail",
                   "right_read_datalabs": "Consulter la liste des environnements de travail"
                   }


class RolesService:

    @staticmethod
    def build_help_text(text_root: str, on_same_level: bool, on_inferior_levels: bool):
        text = text_root
        if on_same_level:
            text = f"{text} sur un périmètre exclusivement"
            if on_inferior_levels:
                text = f"{text.replace(' exclusivement', '')} et ses sous-périmètres"
        elif on_inferior_levels:
            text = f"{text} sur les sous-périmètres exclusivement"
        return text if text != text_root else ""

    def get_help_text_for_right_manage_admin_accesses(self, role):
        return self.build_help_text(text_root="Gérer les accès des administrateurs",
                                    on_same_level=role.right_manage_admin_accesses_same_level,
                                    on_inferior_levels=role.right_manage_admin_accesses_inferior_levels)

    def get_help_text_for_right_manage_data_accesses(self, role):
        return self.build_help_text(text_root="Gérer les accès aux données patients",
                                    on_same_level=role.right_manage_data_accesses_same_level,
                                    on_inferior_levels=role.right_manage_data_accesses_inferior_levels)

    def get_help_text(self, role):
        hierarchy_agnostic_rights = [right for right in all_rights if not (right.endswith('same_level')
                                                                           or right.endswith('inferior_levels')
                                                                           or right.endswith('above_levels'))]
        help_txt = [ROLES_HELP_TEXT.get(r) for r in hierarchy_agnostic_rights if getattr(role, r, False)]

        hierarchy_dependent_texts = [self.get_help_text_for_right_manage_admin_accesses(role),
                                     self.get_help_text_for_right_manage_data_accesses(role)
                                     ]
        help_txt.extend([text for text in hierarchy_dependent_texts if text])
        return help_txt

    @staticmethod
    def role_allows_to_manage_accesses(role):
        return any((role.right_full_admin,
                    role.right_manage_admin_accesses_same_level,
                    role.right_manage_admin_accesses_inferior_levels,
                    role.right_manage_data_accesses_same_level,
                    role.right_manage_data_accesses_inferior_levels))

    def role_allows_to_read_accesses(self, role):
        return self.role_allows_to_manage_accesses(role=role)

    @staticmethod
    def check_role_has_inconsistent_rights(data: dict) -> None:

        def is_full_admin_with_falsy_rights(d: dict) -> bool:
            return d.get("right_full_admin", False) \
                   and any(not d.get(right) for right in all_rights)


        def allow_read_data_pseudo_and_export_nomi(d: dict) -> bool:
            return not d.get("right_read_patient_nominative", False) \
                   and d.get("right_read_patient_pseudonymized", False) \
                   and (d.get("right_export_csv_xlsx_nominative", False)
                        or d.get("right_export_jupyter_nominative", False))

        def allow_search_by_ipp_but_not_read_nomi(d: dict) -> bool:
            return d.get("right_search_patients_by_ipp", False) \
                   and not d.get("right_read_patient_nominative", False)


        def allow_manage_accesses(d: dict) -> bool:
            return any((d.get("right_manage_data_accesses_same_level", False),
                        d.get("right_manage_data_accesses_inferior_levels", False),
                        d.get("right_manage_admin_accesses_same_level", False),
                        d.get("right_manage_admin_accesses_inferior_levels", False)))

        if is_full_admin_with_falsy_rights(data):
            raise IntegrityError("Cannot create a Full Admin role with falsy rights")

        if allow_read_data_pseudo_and_export_nomi(data):
            raise IntegrityError("Cannot create a role allowing to read patient data in pseudo and export nominative data")

        if allow_search_by_ipp_but_not_read_nomi(data):
            raise IntegrityError("Cannot create a role allowing to search by IPP but not read patient data in nominative mode")

        if allow_manage_accesses(data) and not data.get("right_manage_users", False):
            raise IntegrityError("Cannot create a role allowing to manage accesses but not users")


    @staticmethod
    def get_assignable_roles_ids(user: User, perimeter_id: str, all_roles: QuerySet) -> List[int]:
        perimeter = Perimeter.objects.get(id=perimeter_id)
        assignable_roles_ids = [role.id for role in all_roles
                                if accesses_service.can_user_manage_access(user=user,
                                                                           target_access={"role": role, "perimeter": perimeter})]
        return assignable_roles_ids


roles_service = RolesService()
