from __future__ import annotations

from typing import List, Dict

from django.db import models
from django.db.models import Q

from accesses.rights import RightGroup, full_admin_rights, all_rights
from accesses.tools import intersect_queryset_criteria
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
                                                         "de leur données pour la recherche")


def build_help_text(text_root: str, to_same_level: bool, to_inferior_levels: bool, to_above_levels: bool):
    text = text_root
    if to_same_level:
        text = f"{text} sur un périmètre exclusivement"
        if to_inferior_levels:
            text = f"{text.replace(' exclusivement', '')} et ses sous-périmètres"
        if to_above_levels:
            text = f"{text.replace(' exclusivement', '')} et ses périmètres parents"
    elif to_inferior_levels:
        text = f"{text} sur les sous-périmètres exclusivement"
        if to_above_levels:
            text = f"{text.replace(' exclusivement', '')} et les périmètres parents"
    elif to_above_levels:
        text = f"{text} sur les périmètres parents exclusivement"
    if text != text_root:
        return text
    return None


class Role(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)

    right_full_admin = models.BooleanField(default=False, null=False)

    right_read_logs = models.BooleanField(default=False, null=False)

    right_manage_roles = models.BooleanField(default=False, null=False)
    right_read_roles = models.BooleanField(default=False, null=False)

    right_manage_users = models.BooleanField(default=False, null=False)
    right_read_users = models.BooleanField(default=False, null=False)

    right_manage_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_same_level = models.BooleanField(default=False, null=False)

    right_manage_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)

    right_read_accesses_above_levels = models.BooleanField(default=False, null=False)

    right_manage_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_data_accesses_same_level = models.BooleanField(default=False, null=False)

    right_manage_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)

    right_read_patient_nominative = models.BooleanField(default=False, null=False)
    right_read_patient_pseudonymized = models.BooleanField(default=False, null=False)
    right_search_patients_by_ipp = models.BooleanField(default=False, null=False)
    right_read_research_opposed_patient_data = models.BooleanField(default=False, null=False)

    # JUPYTER EXPORT
    right_manage_export_jupyter_accesses = models.BooleanField(default=False, null=False)
    right_export_jupyter_nominative = models.BooleanField(default=False, null=False)
    right_export_jupyter_pseudonymized = models.BooleanField(default=False, null=False)

    # CSV EXPORT
    right_manage_export_csv_accesses = models.BooleanField(default=False, null=False)
    right_export_csv_nominative = models.BooleanField(default=False, null=False)
    right_export_csv_pseudonymized = models.BooleanField(default=False, null=False)

    # datalabs
    right_manage_datalabs = models.BooleanField(default=False, null=False)
    right_read_datalabs = models.BooleanField(default=False, null=False)

    _right_groups = None
    _rights_allowing_to_read_accesses_on_same_level = None
    _rights_allowing_to_read_accesses_on_inferior_levels = None

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
    def q_allow_manage_accesses_on_any_level() -> Q:
        return join_qs([Q(**{f'role__{right.name}': True})
                        for right in all_rights if right.allow_edit_accesses_on_any_level])

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

# -+-+-+-+-+-+-+-+-+-+-+-+-     Requirements to be managed    -+-+-+-+-+-+-+-+-+-+-+-+-

    @property
    def requires_csv_accesses_managing_role_to_be_managed(self):    # requires having: right_manage_export_csv_accesses = True
        return any((self.right_export_csv_nominative,
                    self.right_export_csv_pseudonymized))

    @property
    def requires_jupyter_accesses_managing_role_to_be_managed(self):    # requires having: right_manage_export_jupyter_accesses = True
        return any((self.right_export_jupyter_nominative,
                    self.right_export_jupyter_pseudonymized))

    @property
    def requires_data_accesses_managing_role_to_be_managed(self):    # requires having: right_manage/read_data_accesses_xxx_level = True
        return any((self.right_manage_data_accesses_same_level,
                    self.right_read_data_accesses_same_level,
                    self.right_manage_data_accesses_inferior_levels,
                    self.right_read_data_accesses_inferior_levels,
                    self.right_read_patient_nominative,
                    self.right_read_patient_pseudonymized,
                    self.right_search_patients_by_ipp,
                    self.right_read_research_opposed_patient_data))

    @property
    def requires_admin_accesses_managing_role_to_be_managed(self):
        return any((self.right_manage_admin_accesses_same_level,
                    self.right_read_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels,
                    self.right_read_admin_accesses_inferior_levels,
                    # self.right_read_accesses_above_levels    # todo: process this right differently
                    ))

    @property
    def requires_full_admin_role_to_be_managed(self):
        return any((self.right_manage_roles,
                    self.right_read_logs,
                    self.right_manage_users,
                    self.right_read_datalabs,
                    self.right_manage_datalabs,
                    self.right_manage_export_csv_accesses,
                    self.right_manage_export_jupyter_accesses))

# -+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-

    @property
    def right_groups(self) -> List[RightGroup]:
        """
        get the RightGroups to which belong the rights that are activated on the current Role.
        """
        def get_right_groups(rg: RightGroup):
            res = []
            for right in map(lambda r: r.name, rg.rights):
                if getattr(self, right, False):
                    res.append(rg)
                    break
            return res + sum([get_right_groups(c) for c in rg.child_groups], [])

        if self._right_groups is None:
            self._right_groups = get_right_groups(rg=full_admin_rights)
        return self._right_groups

    @property
    def rights_allowing_to_read_accesses_on_same_level(self) -> List[str]:
        if self._rights_allowing_to_read_accesses_on_same_level is None:
            self._rights_allowing_to_read_accesses_on_same_level = [right.name for right in all_rights
                                                                    if getattr(self, right.name, False)
                                                                    and right.allow_read_accesses_on_same_level]
        return self._rights_allowing_to_read_accesses_on_same_level

    @property
    def rights_allowing_to_read_accesses_on_inferior_levels(self) -> List[str]:
        if self._rights_allowing_to_read_accesses_on_inferior_levels is None:
            self._rights_allowing_to_read_accesses_on_inferior_levels = [right.name for right in all_rights
                                                                         if getattr(self, right.name, False)
                                                                         and right.allow_read_accesses_on_inf_levels]
        return self._rights_allowing_to_read_accesses_on_inferior_levels

    @property
    def unreadable_rights(self) -> List[Dict]:     # todo: understand this
        criteria = [{right.name: True} for right in all_rights]
        for rg in self.right_groups:
            rg_criteria = []
            if any(getattr(self, right.name, False) for right in rg.rights_allowing_reading_accesses):
                for child_group in rg.child_groups:
                    if child_group.child_groups_rights:
                        not_true = dict((right.name, False) for right in child_group.rights)
                        rg_criteria.extend({right.name: True, **not_true} for right in child_group.child_groups_rights)
                rg_criteria.extend({right.name: True} for right in rg.unreadable_rights)
                criteria = intersect_queryset_criteria(criteria, rg_criteria)
        return criteria

    def get_help_text_for_right_manage_admin_accesses(self):
        return build_help_text(text_root="Gérer les accès des administrateurs",
                               to_same_level=self.right_manage_admin_accesses_same_level,
                               to_inferior_levels=self.right_manage_admin_accesses_inferior_levels,
                               to_above_levels=False)

    def get_help_text_for_right_read_admin_accesses(self):
        return build_help_text(text_root="Consulter la liste des accès administrateurs",
                               to_same_level=self.right_read_admin_accesses_same_level,
                               to_inferior_levels=self.right_read_admin_accesses_inferior_levels,
                               to_above_levels=self.right_read_accesses_above_levels)

    def get_help_text_for_right_manage_data_accesses(self):
        return build_help_text(text_root="Gérer les accès aux données patients",
                               to_same_level=self.right_manage_data_accesses_same_level,
                               to_inferior_levels=self.right_manage_data_accesses_inferior_levels,
                               to_above_levels=False)

    def get_help_text_for_right_read_data_accesses(self):
        return build_help_text(text_root="Consulter la liste des accès aux données patients",
                               to_same_level=self.right_read_data_accesses_same_level,
                               to_inferior_levels=self.right_read_data_accesses_inferior_levels,
                               to_above_levels=False)

    @property
    def help_text(self):
        level_agnostic_rights = [r.name for r in all_rights if not (r.name.endswith('same_level')
                                                                    or r.name.endswith('inferior_levels')
                                                                    or r.name.endswith('above_levels'))]
        help_txt = [ROLES_HELP_TEXT.get(r) for r in level_agnostic_rights if self.__dict__.get(r)]

        level_dependent_texts = [self.get_help_text_for_right_manage_admin_accesses() or "",
                                 self.get_help_text_for_right_read_admin_accesses() or "",
                                 self.get_help_text_for_right_manage_data_accesses() or "",
                                 self.get_help_text_for_right_read_data_accesses() or ""]
        help_txt.extend([text for text in level_dependent_texts if text])
        return help_txt
