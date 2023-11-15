from __future__ import annotations

from django.db import models
from django.db.models import Q

from accesses.rights import all_rights
from admin_cohort.models import BaseModel
from admin_cohort.tools import join_qs

ROLES_HELP_TEXT = dict(right_manage_roles="Gérer les rôles",
                       right_read_logs="Lire l'historique des requêtes des utilisateurs",
                       right_manage_users="Gérer la liste des profils/utilisateurs manuels et activer/désactiver les autres.",
                       right_read_users="Consulter la liste des utilisateurs/profils",
                       right_read_patient_nominative="Lire les données patient sous forme nominatives sur son périmètre et ses sous-périmètres",
                       right_read_patient_pseudonymized="Lire les données patient sous forme pseudonymisée sur son périmètre et "
                                                        "ses sous-périmètres",
                       right_search_patients_by_ipp="Utiliser une liste d'IPP comme critère d'une requête Cohort.",
                       right_manage_export_jupyter_accesses="Gérer les accès permettant d'exporter les cohortes vers des environnements Jupyter",
                       right_export_jupyter_nominative="Exporter ses cohortes de patients sous forme nominative vers un environnement Jupyter.",
                       right_export_jupyter_pseudonymized="Exporter ses cohortes de patients sous forme pseudonymisée vers un "
                                                          "environnement Jupyter.",
                       right_manage_export_csv_accesses="Gérer les accès permettant de réaliser des exports de données en format CSV",
                       right_export_csv_nominative="Demander à exporter ses cohortes de patients sous forme nominative en format CSV.",
                       right_export_csv_pseudonymized="Demander à exporter ses cohortes de patients sous forme pseudonymisée en format CSV.",
                       right_read_datalabs="Consulter les informations liées aux environnements de travail",
                       right_manage_datalabs="Gérer les environnements de travail",
                       right_read_research_opposed_patient_data="Détermine le droit de lecture de données des patients opposés à l'utilisation "
                                                                "de leurs données pour la recherche")


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

    right_manage_roles = models.BooleanField(default=False, null=False)
    right_read_roles = models.BooleanField(default=False, null=False)

    right_manage_users = models.BooleanField(default=False, null=False)
    right_read_users = models.BooleanField(default=False, null=False)

    # Admin accesses reading/management
    right_manage_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)

    # todo: process this right differently.
    #       Add write/readonly option on it or maybe add new right:  `right_manage_accesses_above_levels` ?
    right_read_accesses_above_levels = models.BooleanField(default=False, null=False)   #

    # Data accesses reading/management
    right_manage_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)

    # Read patient data
    right_read_patient_nominative = models.BooleanField(default=False, null=False)
    right_read_patient_pseudonymized = models.BooleanField(default=False, null=False)
    right_search_patients_by_ipp = models.BooleanField(default=False, null=False)
    right_read_research_opposed_patient_data = models.BooleanField(default=False, null=False)

    # Jupyter exports
    right_manage_export_jupyter_accesses = models.BooleanField(default=False, null=False)
    right_export_jupyter_nominative = models.BooleanField(default=False, null=False)
    right_export_jupyter_pseudonymized = models.BooleanField(default=False, null=False)

    # CSV exports
    right_manage_export_csv_accesses = models.BooleanField(default=False, null=False)
    right_export_csv_nominative = models.BooleanField(default=False, null=False)
    right_export_csv_pseudonymized = models.BooleanField(default=False, null=False)

    # Datalabs
    right_manage_datalabs = models.BooleanField(default=False, null=False)
    right_read_datalabs = models.BooleanField(default=False, null=False)

    def has_any_global_management_right(self):
        return any((self.right_full_admin,
                    self.right_manage_roles,
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
        return Q(role__right_read_research_opposed_patient_data=True)

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
    def q_allow_manage_export_accesses() -> Q:
        return join_qs([Q(role__right_manage_export_csv_accesses=True),
                        Q(role__right_manage_export_jupyter_accesses=True)])

    @staticmethod
    def q_impact_inferior_levels() -> Q:
        return join_qs([Q(**{f"role__{right.name}": True})
                        for right in all_rights if right.impact_inferior_levels])

    @property
    def can_manage_accesses(self):
        return any((self.right_full_admin,
                    self.right_manage_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels,
                    self.right_manage_data_accesses_same_level,
                    self.right_manage_data_accesses_inferior_levels,
                    self.right_manage_export_jupyter_accesses,
                    self.right_manage_export_csv_accesses))

    @property
    def can_read_accesses(self):
        return self.can_manage_accesses \
               or any((self.right_read_admin_accesses_same_level,
                       self.right_read_admin_accesses_inferior_levels,
                       self.right_read_accesses_above_levels,
                       self.right_read_data_accesses_same_level,
                       self.right_read_data_accesses_inferior_levels))

# -+-+-+-+-+-+-+-+-+-+-+-+-     Roles requirements to be managed    -+-+-+-+-+-+-+-+-+-+-+-+-

    @property
    def requires_csv_accesses_managing_role_to_be_managed(self):
        # requires having: right_manage_export_csv_accesses = True
        return any((self.right_export_csv_nominative,
                    self.right_export_csv_pseudonymized))

    @property
    def requires_jupyter_accesses_managing_role_to_be_managed(self):
        # requires having: right_manage_export_jupyter_accesses = True
        return any((self.right_export_jupyter_nominative,
                    self.right_export_jupyter_pseudonymized))

    @property
    def requires_data_accesses_managing_role_to_be_managed(self):
        # requires having: right_manage/read_data_accesses_same/inf_level = True
        return any((self.right_read_patient_nominative,
                    self.right_read_patient_pseudonymized,
                    self.right_search_patients_by_ipp,
                    self.right_read_research_opposed_patient_data))

    @property
    def requires_admin_accesses_managing_role_to_be_managed(self):
        # requires having: right_manage/read_admin_accesses_same/inf_level = True
        return any((self.right_manage_data_accesses_same_level,
                    self.right_read_data_accesses_same_level,
                    self.right_manage_data_accesses_inferior_levels,
                    self.right_read_data_accesses_inferior_levels))

    @property
    def requires_full_admin_role_to_be_managed(self):
        # requires having: right_full_admin = True
        return any((self.right_full_admin,
                    self.right_read_logs,
                    self.right_manage_roles,
                    self.right_read_roles,
                    self.right_manage_users,
                    self.right_read_users,
                    self.right_manage_datalabs,
                    self.right_read_datalabs,
                    self.right_manage_export_csv_accesses,
                    self.right_manage_export_jupyter_accesses,
                    self.right_manage_admin_accesses_same_level,
                    self.right_read_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels,
                    self.right_read_admin_accesses_inferior_levels,
                    # self.right_read_accesses_above_levels    # todo: process this right differently
                    ))

# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-

    def get_help_text_for_right_manage_admin_accesses(self):
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
                and "Consulter la liste de tous les accès définis sur les périmètres parents" or ""

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
