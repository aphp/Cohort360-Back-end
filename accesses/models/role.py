from __future__ import annotations

from typing import List, Dict, Callable

from django.db import models
from django.db.models import Q

from accesses.rights import RightGroup, main_admin_rights, all_rights, Right
from admin_cohort.models import BaseModel
from admin_cohort.tools import join_qs

ROLES_HELP_TEXT = dict(right_manage_roles="Gérer les rôles",
                       right_read_logs="Lire l'historique des requêtes des utilisateurs",
                       right_add_users="Ajouter un profil manuel pour un utilisateur de l'AP-HP.",
                       right_edit_users="Modifier les profils manuels et activer/désactiver les autres.",
                       right_read_users="Consulter la liste des utilisateurs/profils",
                       right_read_patient_nominative="Lire les données patient sous forme nominatives sur son périmètre et ses sous-périmètres",
                       right_read_patient_pseudo_anonymised="Lire les données patient sous forme pseudonymisée sur son périmètre et "
                                                            "ses sous-périmètres",
                       right_search_patients_by_ipp="Utiliser une liste d'IPP comme critère d'une requête Cohort.",
                       right_manage_export_jupyter_accesses="Gérer les accès permettant d'exporter les cohortes vers des environnements Jupyter",
                       right_export_jupyter_nominative="Exporter ses cohortes de patients sous forme nominative vers un environnement Jupyter.",
                       right_export_jupyter_pseudo_anonymised="Exporter ses cohortes de patients sous forme pseudonymisée vers un "
                                                              "environnement Jupyter.",
                       right_manage_export_csv_accesses="Gérer les accès permettant de réaliser des exports de données en format CSV",
                       right_export_csv_nominative="Demander à exporter ses cohortes de patients sous forme nominative en format CSV.",
                       right_export_csv_pseudo_anonymised="Demander à exporter ses cohortes de patients sous forme pseudonymisée en format CSV.",
                       right_read_env_unix_users="Consulter les informations liées aux environnements de travail",
                       right_manage_env_unix_users="Gérer les environnements de travail",
                       right_manage_env_user_links="Gérer les accès des utilisateurs aux environnements de travail",
                       right_read_opposing_patient="Détermine le droit de lecture des patients opposés à l'utilisation "
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


def format_prefix(prefix: str) -> str:
    return prefix and f"{prefix}__" or ""


class Role(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    invalid_reason = models.TextField(blank=True, null=True)

    right_manage_roles = models.BooleanField(default=False, null=False)
    right_read_logs = models.BooleanField(default=False, null=False)

    right_add_users = models.BooleanField(default=False, null=False)
    right_edit_users = models.BooleanField(default=False, null=False)
    right_read_users = models.BooleanField(default=False, null=False)

    right_manage_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_admin_accesses_inferior_levels = models.BooleanField(default=False, null=False)

    right_read_admin_accesses_above_levels = models.BooleanField(default=False, null=False)

    right_manage_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_read_data_accesses_same_level = models.BooleanField(default=False, null=False)
    right_manage_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)
    right_read_data_accesses_inferior_levels = models.BooleanField(default=False, null=False)

    right_read_patient_nominative = models.BooleanField(default=False, null=False)
    right_read_patient_pseudo_anonymised = models.BooleanField(default=False, null=False)
    right_search_patients_by_ipp = models.BooleanField(default=False, null=False)
    right_read_opposing_patient = models.BooleanField(default=False, null=False)

    # JUPYTER TRANSFER
    right_manage_export_jupyter_accesses = models.BooleanField(default=False, null=False)
    right_export_jupyter_nominative = models.BooleanField(default=False, null=False)
    right_export_jupyter_pseudo_anonymised = models.BooleanField(default=False, null=False)

    # CSV EXPORT
    right_manage_export_csv_accesses = models.BooleanField(default=False, null=False)
    right_export_csv_nominative = models.BooleanField(default=False, null=False)
    right_export_csv_pseudo_anonymised = models.BooleanField(default=False, null=False)

    # environments
    right_read_env_unix_users = models.BooleanField(default=False, null=False)
    right_manage_env_unix_users = models.BooleanField(default=False, null=False)
    right_manage_env_user_links = models.BooleanField(default=False, null=False)

    _readable_right_set = None
    _right_groups = None
    _inf_level_readable_rights = None
    _same_level_readable_rights = None

    @classmethod
    def is_read_patient_role_nominative(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_read_patient_nominative': True})])

    @classmethod
    def is_read_patient_role_pseudo(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_read_patient_pseudo_anonymised': True,
                             f'{formatted_prefix}right_read_patient_nominative': False})])

    @classmethod
    def is_read_patient_role(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_read_patient_pseudo_anonymised': True}),
                        Q(**{f'{formatted_prefix}right_read_patient_nominative': True})])

    @classmethod
    def is_search_ipp_role(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_search_patients_by_ipp': True})])

    @classmethod
    def is_search_opposing_patient_role(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_read_opposing_patient': True})])

    @classmethod
    def is_export_csv_nominative_role(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_export_csv_nominative': True})])

    @classmethod
    def is_export_csv_pseudo_role(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_export_csv_nominative': True}),
                        Q(**{f'{formatted_prefix}right_export_csv_pseudo_anonymised': True})])

    @classmethod
    def is_export_jupyter_nominative_role(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_export_jupyter_nominative': True})])

    @classmethod
    def is_export_jupyter_pseudo_role(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_export_jupyter_nominative': True}),
                        Q(**{f'{formatted_prefix}right_export_jupyter_pseudo_anonymised': True})])

    @classmethod
    def is_manage_role_any_level(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_manage_export_jupyter_accesses': True}),
                        Q(**{f'{formatted_prefix}right_manage_export_csv_accesses': True})])

    @classmethod
    def is_manage_role_same_level(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_manage_data_accesses_same_level': True}),
                        Q(**{f'{formatted_prefix}right_manage_admin_accesses_same_level': True}),
                        Q(**{f'{formatted_prefix}right_read_data_accesses_same_level': True}),
                        Q(**{f'{formatted_prefix}right_read_admin_accesses_same_level': True})])

    @classmethod
    def is_manage_role_inf_level(cls, prefix: str = "") -> Q:
        formatted_prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{formatted_prefix}right_manage_admin_accesses_inferior_levels': True}),
                        Q(**{f'{formatted_prefix}right_read_admin_accesses_inferior_levels': True}),
                        Q(**{f'{formatted_prefix}right_manage_data_accesses_inferior_levels': True}),
                        Q(**{f'{formatted_prefix}right_read_data_accesses_inferior_levels': True})])

    @classmethod
    def all_rights(cls):
        return [f.name for f in cls._meta.fields if f.name.startswith("right_")]

    @classmethod
    def manage_on_inf_levels_query(cls, prefix: str = None) -> Q:
        prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{prefix}{r.name}': True}) for r in [right for right in all_rights
                                                                   if right.allow_edit_accesses_on_inf_levels
                                                                   or right.allow_read_rights_on_inf_levels]])

    @classmethod
    def manage_on_same_level_query(cls, prefix: str = None) -> Q:
        prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{prefix}{r.name}': True}) for r in [right for right in all_rights
                                                                   if right.allow_edit_accesses_on_same_level
                                                                   or right.allow_read_rights_on_same_level]])

    @classmethod
    def edit_on_lower_levels_query(cls, prefix: str = None, additional: Dict = None) -> Q:
        additional = additional or {}
        prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{prefix}{r.name}': True, **additional}) for r in [right for right in all_rights
                                                                                 if right.allow_edit_accesses_on_inf_levels]])

    @classmethod
    def edit_on_same_level_query(cls, prefix: str = None, additional: Dict = None) -> Q:
        additional = additional or {}
        prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{prefix}{r.name}': True, **additional}) for r in [right for right in all_rights
                                                                                 if right.allow_edit_accesses_on_same_level]])

    @classmethod
    def manage_on_any_level_query(cls, prefix: str = None) -> Q:
        prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{prefix}{r.name}': True}) for r in [right for right in all_rights
                                                                   if right.allow_read_rights_on_any_level
                                                                   or right.allow_edit_accesses_on_any_level]])

    @classmethod
    def edit_on_any_level_query(cls, prefix: str = None) -> Q:
        prefix = format_prefix(prefix)
        return join_qs([Q(**{f'{prefix}{r.name}': True}) for r in [right for right in all_rights if right.allow_edit_accesses_on_any_level]])

    @property
    def right_groups(self) -> List[RightGroup]:
        def get_right_group(rg: RightGroup):
            res = []
            for r in map(lambda x: x.name, rg.rights):
                if getattr(self, r, False):
                    res.append(rg)
                    break
            return res + sum([get_right_group(c) for c in rg.children], [])

        if self._right_groups is None:
            self._right_groups = get_right_group(main_admin_rights)
        return self._right_groups

    def get_specific_readable_rights(self, getter: Callable[[RightGroup], List[Right]]) -> List[str]:
        res = []
        for rg in self.right_groups:
            for right in getter(rg):
                if getattr(self, right.name, False):
                    readable_rights = sum([[r.name for r in c.rights] for c in rg.children], [])
                    if any([len(c.children) for c in rg.children]):
                        readable_rights.append("right_read_users")
                    res.extend(readable_rights)
        return list(set(res))

    @property
    def inf_level_readable_rights(self) -> List[str]:
        """
        Returns rights that, when bound to an access through a Role,
        this role allows a user to read
        on the children of the perimeter of the access this role is bound to
        :return:
        """
        if self._inf_level_readable_rights is None:
            self._inf_level_readable_rights = self.get_specific_readable_rights(lambda rg: rg.rights_read_on_inferior_levels)
        return self._inf_level_readable_rights

    @property
    def same_level_readable_rights(self) -> List[str]:
        """
        Returns rights that, when bound to an access through a Role,
        this role allows a user to read
        on the same perimeter of the access this role is bound to
        :return:
        """
        if self._same_level_readable_rights is None:
            self._same_level_readable_rights = self.get_specific_readable_rights(lambda rg: rg.rights_read_on_same_level)
        return self._same_level_readable_rights

    @property
    def unreadable_rights(self) -> List[Dict]:
        """
        Returns rights that, when bound to an access through a Role,
        this role allows a user to read
        on the same perimeter of the access this role is bound to
        :return:
        """
        from accesses.models import intersect_queryset_criteria

        criteria = list({r.name: True} for r in all_rights)
        for rg in self.right_groups:
            rg_criteria = []
            if any(getattr(self, right.name) for right in rg.rights_allowing_reading_accesses):
                for c in rg.children:
                    if len(c.children_rights):
                        not_true = dict((r.name, False) for r in c.rights)
                        rg_criteria.extend({r.name: True, **not_true} for r in c.children_rights)
                rg_criteria.extend({r.name: True} for r in rg.unreadable_rights)
                criteria = intersect_queryset_criteria(criteria, rg_criteria)

        return criteria

    @property
    def can_manage_other_accesses(self):
        return self.right_manage_roles \
               or self.right_manage_admin_accesses_same_level \
               or self.right_manage_admin_accesses_inferior_levels \
               or self.right_manage_data_accesses_same_level \
               or self.right_manage_data_accesses_inferior_levels \
               or self.right_manage_export_jupyter_accesses \
               or self.right_manage_export_csv_accesses

    @property
    def can_read_other_accesses(self):
        return self.right_manage_roles \
               or self.right_read_admin_accesses_same_level \
               or self.right_read_admin_accesses_inferior_levels \
               or self.right_read_admin_accesses_above_levels \
               or self.right_read_data_accesses_same_level \
               or self.right_read_data_accesses_inferior_levels \
               or self.right_manage_export_jupyter_accesses \
               or self.right_manage_export_csv_accesses

    @property
    def requires_csv_accesses_managing_role_to_be_managed(self):
        return any([self.right_export_csv_nominative,
                    self.right_export_csv_pseudo_anonymised])

    @property
    def requires_jupyter_accesses_managing_role_to_be_managed(self):
        return any([self.right_export_jupyter_nominative,
                    self.right_export_jupyter_pseudo_anonymised])

    # @property
    # def requires_admin_role_to_be_managed(self):
    #     return any([self.right_read_patient_nominative,
    #                 self.right_search_patients_by_ipp,
    #                 self.right_read_patient_pseudo_anonymised])

    @property
    def requires_data_accesses_managing_role_to_be_managed(self):
        return any([self.right_manage_data_accesses_same_level,
                    self.right_read_data_accesses_same_level,
                    self.right_manage_data_accesses_inferior_levels,
                    self.right_read_data_accesses_inferior_levels])

    @property
    def requires_admin_accesses_managing_role_to_be_managed(self):
        return any([self.right_manage_admin_accesses_same_level,
                    self.right_read_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels,
                    self.right_read_admin_accesses_inferior_levels,
                    self.right_read_admin_accesses_above_levels])

    @property
    def requires_main_admin_role_to_be_managed(self):
        return any([self.right_manage_roles,
                    self.right_read_logs,
                    self.right_add_users,
                    self.right_edit_users,
                    self.right_manage_admin_accesses_same_level,
                    self.right_read_admin_accesses_same_level,
                    self.right_manage_admin_accesses_inferior_levels,
                    self.right_read_admin_accesses_inferior_levels,
                    self.right_read_admin_accesses_above_levels,
                    self.right_read_env_unix_users,
                    self.right_manage_env_unix_users,
                    self.right_manage_env_user_links,
                    self.right_manage_export_jupyter_accesses,
                    self.right_manage_export_csv_accesses])

    @property
    def requires_any_admin_mng_role_to_be_managed(self):
        # to be managed, the role requires access with
        # main admin or admin manager
        return self.right_read_users

    def get_help_text_for_right_manage_admin_accesses(self):
        return build_help_text(text_root="Gérer les accès des administrateurs",
                               to_same_level=self.right_manage_admin_accesses_same_level,
                               to_inferior_levels=self.right_manage_admin_accesses_inferior_levels,
                               to_above_levels=False)

    def get_help_text_for_right_read_admin_accesses(self):
        return build_help_text(text_root="Consulter la liste des accès administrateurs",
                               to_same_level=self.right_read_admin_accesses_same_level,
                               to_inferior_levels=self.right_read_admin_accesses_inferior_levels,
                               to_above_levels=self.right_read_admin_accesses_above_levels)

    def get_help_text_for_right_read_data_accesses(self):
        return build_help_text(text_root="Consulter la liste des accès aux données patients",
                               to_same_level=self.right_read_data_accesses_same_level,
                               to_inferior_levels=self.right_read_data_accesses_inferior_levels,
                               to_above_levels=False)

    def get_help_text_for_right_manage_data_accesses(self):
        return build_help_text(text_root="Gérer les accès aux données patients",
                               to_same_level=self.right_manage_data_accesses_same_level,
                               to_inferior_levels=self.right_manage_data_accesses_inferior_levels,
                               to_above_levels=False)

    @property
    def help_text(self):
        level_agnostic_rights = [r for r in Role.all_rights() if not (r.endswith('same_level')
                                                                      or r.endswith('inferior_levels')
                                                                      or r.endswith('above_levels'))]
        help_txt = [ROLES_HELP_TEXT.get(r) for r in level_agnostic_rights if self.__dict__.get(r)]

        level_dependent_texts = [self.get_help_text_for_right_manage_admin_accesses() or "",
                                 self.get_help_text_for_right_read_admin_accesses() or "",
                                 self.get_help_text_for_right_manage_data_accesses() or "",
                                 self.get_help_text_for_right_read_data_accesses() or ""]
        help_txt.extend([text for text in level_dependent_texts if text])
        return help_txt
