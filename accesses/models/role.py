from __future__ import annotations

from typing import List

from django.db import models
from django.db.models import Q, UniqueConstraint

from accesses.services.shared import all_rights, right_groups_service
from admin_cohort.models import BaseModel
from admin_cohort.tools import join_qs

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


def build_help_text(text_root: str, on_same_level: bool, on_inferior_levels: bool):
    text = text_root
    if on_same_level:
        text = f"{text} sur un périmètre exclusivement"
        if on_inferior_levels:
            text = f"{text.replace(' exclusivement', '')} et ses sous-périmètres"
    elif on_inferior_levels:
        text = f"{text} sur les sous-périmètres exclusivement"
    return text if text != text_root else ""


class Role(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    right_full_admin = models.BooleanField(default=False, null=False)
    right_read_logs = models.BooleanField(default=False, null=False)
    right_manage_users = models.BooleanField(default=False, null=False)
    right_read_users = models.BooleanField(default=False, null=False)
    # Datalabs
    right_manage_datalabs = models.BooleanField(default=False, null=False)
    right_read_datalabs = models.BooleanField(default=False, null=False)
    # CSV exports
    right_manage_export_csv_accesses = models.BooleanField(default=False, null=False)
    right_export_csv_nominative = models.BooleanField(default=False, null=False)
    right_export_csv_pseudonymized = models.BooleanField(default=False, null=False)
    # Jupyter exports
    right_manage_export_jupyter_accesses = models.BooleanField(default=False, null=False)
    right_export_jupyter_nominative = models.BooleanField(default=False, null=False)
    right_export_jupyter_pseudonymized = models.BooleanField(default=False, null=False)
    # Administration accesses reading/management
    right_manage_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_accesses_above_levels = models.BooleanField(default=False, null=False)
    # Data accesses reading/management
    right_manage_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    # Read patient data
    right_read_patient_nominative = models.BooleanField(default=False, null=False)
    right_read_patient_pseudonymized = models.BooleanField(default=False, null=False)
    right_search_patients_by_ipp = models.BooleanField(default=False, null=False)
    right_search_opposed_patients = models.BooleanField(default=False, null=False)

    class Meta:
        constraints = [UniqueConstraint(name="unique_name",
                                        fields=["name"],
                                        condition=Q(delete_datetime__isnull=True)),
                       UniqueConstraint(name="unique_rights_combination",
                                        fields=[right.name for right in all_rights],
                                        condition=Q(delete_datetime__isnull=True))]

    def __eq__(self, other_role) -> bool:
        return all(getattr(self, right.name, False) == getattr(other_role, right.name, False)
                   for right in all_rights)

    def __gt__(self, other_role) -> bool:
        return right_groups_service.does_role1_prime_over_role2(role1=self, role2=other_role)

    def has_any_global_management_right(self):
        return any((self.right_full_admin,
                    self.right_manage_users,
                    self.right_manage_datalabs,
                    self.right_manage_export_csv_accesses,
                    self.right_manage_export_jupyter_accesses))

    def has_any_level_dependent_management_right(self):
        return any((self.right_manage_data_accesses_same_level,
                    self.right_manage_data_accesses_inferior_levels,
                    self.right_manage_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels))

    @staticmethod
    def q_allow_read_patient_data_nominative() -> Q:
        return Q(role__right_read_patient_nominative=True)

    @staticmethod
    def q_allow_read_patient_data_pseudo() -> Q:
        return Q(role__right_read_patient_pseudonymized=True)

    @staticmethod
    def q_allow_search_patients_by_ipp() -> Q:
        return Q(role__right_search_patients_by_ipp=True)

    @staticmethod
    def q_allow_read_research_opposed_patient_data() -> Q:
        return Q(role__right_search_opposed_patients=True)

    @staticmethod
    def q_allow_export_csv_nominative() -> Q:
        return Q(role__right_export_csv_nominative=True)

    @staticmethod
    def q_allow_export_csv_pseudo() -> Q:
        return join_qs([Q(role__right_export_csv_nominative=True),
                        Q(role__right_export_csv_pseudonymized=True)])

    @staticmethod
    def q_allow_export_jupyter_nominative() -> Q:
        return Q(role__right_export_jupyter_nominative=True)

    @staticmethod
    def q_allow_export_jupyter_pseudo() -> Q:
        return join_qs([Q(role__right_export_jupyter_nominative=True),
                        Q(role__right_export_jupyter_pseudonymized=True)])

    @staticmethod
    def q_allow_manage_accesses_on_same_level() -> Q:
        return join_qs([Q(**{f'role__{right.name}': True})
                        for right in all_rights if right.allow_edit_accesses_on_same_level])

    @staticmethod
    def q_allow_manage_accesses_on_inf_levels() -> Q:
        return join_qs([Q(**{f'role__{right.name}': True})
                        for right in all_rights if right.allow_edit_accesses_on_inf_levels])

    @staticmethod
    def q_allow_read_accesses_on_same_level() -> Q:
        return join_qs([Q(**{f'role__{right.name}': True}) for right in all_rights
                        if right.allow_read_accesses_on_same_level or right.allow_edit_accesses_on_same_level])

    @staticmethod
    def q_allow_read_accesses_on_inf_levels() -> Q:
        return join_qs([Q(**{f'role__{right.name}': True}) for right in all_rights
                        if right.allow_read_accesses_on_inf_levels or right.allow_edit_accesses_on_inf_levels])

    @staticmethod
    def q_allow_manage_export_accesses() -> Q:
        return join_qs([Q(role__right_manage_export_csv_accesses=True),
                        Q(role__right_manage_export_jupyter_accesses=True)])

    @staticmethod
    def q_impact_inferior_levels() -> Q:
        return join_qs([Q(**{f"role__{right.name}": True})
                        for right in all_rights if right.impact_inferior_levels])

    def get_help_text_for_right_manage_admin_accesses(self):                                            # todo: move to     roles_service       /!\
        return build_help_text(text_root="Gérer les accès des administrateurs",
                               on_same_level=self.right_manage_admin_accesses_same_level,
                               on_inferior_levels=self.right_manage_admin_accesses_inferior_levels)

    def get_help_text_for_right_read_admin_accesses(self):
        return build_help_text(text_root="Consulter la liste des accès administrateurs",
                               on_same_level=self.right_read_admin_accesses_same_level,
                               on_inferior_levels=self.right_read_admin_accesses_inferior_levels)

    def get_help_text_for_right_manage_data_accesses(self):
        return build_help_text(text_root="Gérer les accès aux données patients",
                               on_same_level=self.right_manage_data_accesses_same_level,
                               on_inferior_levels=self.right_manage_data_accesses_inferior_levels)

    def get_help_text_for_right_read_data_accesses(self):
        return build_help_text(text_root="Consulter la liste des accès aux données patients",
                               on_same_level=self.right_read_data_accesses_same_level,
                               on_inferior_levels=self.right_read_data_accesses_inferior_levels)

    def get_help_text_for_right_read_accesses_above_levels(self):
        return self.right_read_accesses_above_levels \
                and "Consulter la liste des accès définis sur les périmètres parents d'un périmètre P" or ""

    @property
    def help_text(self):
        hierarchy_agnostic_rights = [r.name for r in all_rights if not (r.name.endswith('same_level')
                                                                        or r.name.endswith('inferior_levels')
                                                                        or r.name.endswith('above_levels'))]
        help_txt = [ROLES_HELP_TEXT.get(r) for r in hierarchy_agnostic_rights if self.__dict__.get(r)]

        hierarchy_dependent_texts = [self.get_help_text_for_right_manage_admin_accesses(),
                                     self.get_help_text_for_right_read_admin_accesses(),
                                     self.get_help_text_for_right_manage_data_accesses(),
                                     self.get_help_text_for_right_read_data_accesses(),
                                     self.get_help_text_for_right_read_accesses_above_levels()]
        help_txt.extend([text for text in hierarchy_dependent_texts if text])
        return help_txt
