from typing import List

from django.db.models import QuerySet

from accesses.models import Perimeter
from accesses.services.accesses import accesses_service
from accesses.services.shared import all_rights
from admin_cohort.models import User

ROLES_HELP_TEXT = dict(right_full_admin="Super user",
                       right_read_logs="Lire l'historique des requêtes des utilisateurs",
                       right_manage_users="Gérer la liste des utilisateurs/profils",
                       right_read_users="Consulter la liste des utilisateurs/profils",
                       right_read_patient_nominative="Lire les données patient sous forme nominatives sur son périmètre et ses sous-périmètres",
                       right_read_patient_pseudonymized="Lire les données patient sous forme pseudonymisée sur son périmètre et "
                                                        "ses sous-périmètres",
                       right_search_patients_by_ipp="Utiliser une liste d'IPP comme critère d'une requête Cohort.",
                       right_search_opposed_patients="Détermine le droit de chercher les patients opposés à l'utilisation "
                                                     "de leurs données pour la recherche",
                       right_manage_export_jupyter_accesses="Gérer les accès permettant d'exporter les cohortes vers des environnements Jupyter",
                       right_export_jupyter_nominative="Exporter ses cohortes de patients sous forme nominative vers un environnement Jupyter.",
                       right_export_jupyter_pseudonymized="Exporter ses cohortes de patients sous forme pseudonymisée vers un environnement Jupyter.",
                       right_manage_export_csv_accesses="Gérer les accès permettant de réaliser des exports de données en format CSV",
                       right_export_csv_nominative="Demander à exporter ses cohortes de patients sous forme nominative en format CSV.",
                       right_export_csv_pseudonymized="Demander à exporter ses cohortes de patients sous forme pseudonymisée en format CSV.",
                       right_manage_datalabs="Gérer les environnements de travail",
                       right_read_datalabs="Consulter la liste des environnements de travail")


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

    def get_help_text_for_right_read_admin_accesses(self, role):
        return self.build_help_text(text_root="Consulter la liste des accès administrateurs",
                                    on_same_level=role.right_read_admin_accesses_same_level,
                                    on_inferior_levels=role.right_read_admin_accesses_inferior_levels)

    def get_help_text_for_right_manage_data_accesses(self, role):
        return self.build_help_text(text_root="Gérer les accès aux données patients",
                                    on_same_level=role.right_manage_data_accesses_same_level,
                                    on_inferior_levels=role.right_manage_data_accesses_inferior_levels)

    def get_help_text_for_right_read_data_accesses(self, role):
        return self.build_help_text(text_root="Consulter la liste des accès aux données patients",
                                    on_same_level=role.right_read_data_accesses_same_level,
                                    on_inferior_levels=role.right_read_data_accesses_inferior_levels)

    @staticmethod
    def get_help_text_for_right_read_accesses_above_levels(role):
        return role.right_read_accesses_above_levels \
                and "Consulter la liste des accès définis sur les périmètres parents d'un périmètre P" or ""

    def get_help_text(self, role):
        hierarchy_agnostic_rights = [r.name for r in all_rights if not (r.name.endswith('same_level')
                                                                        or r.name.endswith('inferior_levels')
                                                                        or r.name.endswith('above_levels'))]
        help_txt = [ROLES_HELP_TEXT.get(r) for r in hierarchy_agnostic_rights if getattr(role, r, False)]

        hierarchy_dependent_texts = [self.get_help_text_for_right_manage_admin_accesses(role),
                                     self.get_help_text_for_right_read_admin_accesses(role),
                                     self.get_help_text_for_right_manage_data_accesses(role),
                                     self.get_help_text_for_right_read_data_accesses(role),
                                     self.get_help_text_for_right_read_accesses_above_levels(role)]
        help_txt.extend([text for text in hierarchy_dependent_texts if text])
        return help_txt

    @staticmethod
    def role_allows_to_manage_accesses(role):
        return any((role.right_full_admin,
                    role.right_manage_admin_accesses_same_level,
                    role.right_manage_admin_accesses_inferior_levels,
                    role.right_manage_data_accesses_same_level,
                    role.right_manage_data_accesses_inferior_levels,
                    role.right_manage_export_jupyter_accesses,
                    role.right_manage_export_csv_accesses))

    def role_allows_to_read_accesses(self, role):
        return self.role_allows_to_manage_accesses(role=role) \
            or any((role.right_read_admin_accesses_same_level,
                    role.right_read_admin_accesses_inferior_levels,
                    role.right_read_data_accesses_same_level,
                    role.right_read_data_accesses_inferior_levels,
                    role.right_read_accesses_above_levels))

    @staticmethod
    def role_has_inconsistent_rights(data: dict) -> bool:
        is_full_admin_with_falsy_rights = (data.get("right_full_admin")
                                           and any(not data.get(r.name) for r in all_rights))

        allow_read_data_pseudo_and_export_nomi = not data.get("right_read_patient_nominative") \
                                                 and data.get("right_read_patient_pseudonymized") \
                                                 and (data.get("right_export_csv_nominative")
                                                      or data.get("right_export_jupyter_nominative"))

        allow_manage_accesses = any((data.get("right_manage_data_accesses_same_level"),
                                     data.get("right_manage_data_accesses_inferior_levels"),
                                     data.get("right_manage_admin_accesses_same_level"),
                                     data.get("right_manage_admin_accesses_inferior_levels"),
                                     data.get("right_manage_export_csv_accesses"),
                                     data.get("right_manage_export_jupyter_accesses")))

        allow_read_accesses = any((data.get("right_read_data_accesses_same_level"),
                                   data.get("right_read_data_accesses_inferior_levels"),
                                   data.get("right_read_admin_accesses_same_level"),
                                   data.get("right_read_admin_accesses_inferior_levels"),
                                   data.get("right_read_accesses_above_levels")))

        allow_manage_users = data.get("right_manage_users")
        allow_read_users = data.get("right_read_users")

        return is_full_admin_with_falsy_rights \
            or allow_read_data_pseudo_and_export_nomi \
            or (allow_manage_accesses and not allow_manage_users) \
            or (allow_read_accesses and not allow_read_users)

    @staticmethod
    def get_assignable_roles_ids(user: User, perimeter_id: str, queryset: QuerySet) -> List[int]:
        perimeter = Perimeter.objects.get(id=perimeter_id)
        assignable_roles_ids = [role.id for role in queryset
                                if accesses_service.can_user_manage_access(user=user,
                                                                           target_access=dict(role=role, perimeter=perimeter))]
        return assignable_roles_ids


roles_service = RolesService()
