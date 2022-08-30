from __future__ import annotations
from typing import List, Dict, Callable

from django.db import models
from django.db.models import Q

from accesses.rights import RightGroup, main_admin_rights, all_rights, Right
from admin_cohort.models import BaseModel
from admin_cohort.tools import join_qs


def right_field():
    return models.BooleanField(default=False, null=False)


class Role(BaseModel):
    id = models.AutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    invalid_reason = models.TextField(blank=True, null=True)

    right_edit_roles = right_field()
    right_read_logs = right_field()

    right_add_users = right_field()
    right_edit_users = right_field()
    right_read_users = right_field()

    right_manage_admin_accesses_same_level = right_field()
    right_read_admin_accesses_same_level = right_field()
    right_manage_admin_accesses_inferior_levels = right_field()
    right_read_admin_accesses_inferior_levels = right_field()

    right_manage_data_accesses_same_level = right_field()
    right_read_data_accesses_same_level = right_field()
    right_manage_data_accesses_inferior_levels = right_field()
    right_read_data_accesses_inferior_levels = right_field()

    right_read_patient_nominative = right_field()
    right_read_patient_pseudo_anonymised = right_field()
    right_search_patient_with_ipp = right_field()

    # JUPYTER TRANSFER
    right_manage_review_transfer_jupyter = right_field()
    right_review_transfer_jupyter = right_field()
    right_manage_transfer_jupyter = right_field()
    right_transfer_jupyter_nominative = right_field()
    right_transfer_jupyter_pseudo_anonymised = right_field()

    # CSV EXPORT
    right_manage_review_export_csv = right_field()
    right_review_export_csv = right_field()
    right_manage_export_csv = right_field()
    right_export_csv_nominative = right_field()
    right_export_csv_pseudo_anonymised = right_field()

    # environments
    right_read_env_unix_users = right_field()
    right_manage_env_unix_users = right_field()
    right_manage_env_user_links = right_field()

    _readable_right_set = None
    _right_groups = None
    _inf_level_readable_rights = None
    _same_level_readable_rights = None

    class Meta:
        managed = True

    @classmethod
    def all_rights(cls):
        return [f.name for f in cls._meta.fields if f.name.startswith("right_")]

    @classmethod
    def impact_lower_levels_query(cls, prefix: str = None) -> Q:
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{r.name}': True})
            for r in [right for right in all_rights
                      if right.impact_lower_levels]
        ])

    @classmethod
    def manage_on_lower_levels_query(cls, prefix: str = None) -> Q:
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{r.name}': True})
            for r in [right for right in all_rights
                      if right.allow_edit_rights_on_inf_levels
                      or right.allow_read_rights_on_inf_levels]
        ])

    @classmethod
    def manage_on_same_level_query(cls, prefix: str = None) -> Q:
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{r.name}': True})
            for r in [right for right in all_rights
                      if right.allow_edit_rights_on_same_level
                      or right.allow_read_rights_on_same_level]
        ])

    @classmethod
    def edit_on_lower_levels_query(cls, prefix: str = None,
                                   additional: Dict = None) -> Q:
        additional = additional or dict()
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{r.name}': True, **additional})
            for r in [right for right in all_rights
                      if right.allow_edit_rights_on_inf_levels]
        ])

    @classmethod
    def edit_on_same_level_query(cls, prefix: str = None,
                                 additional: Dict = None) -> Q:
        additional = additional or dict()
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{r.name}': True, **additional})
            for r in [right for right in all_rights
                      if right.allow_edit_rights_on_same_level]
        ])

    @classmethod
    def manage_on_any_level_query(cls, prefix: str = None) -> Q:
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{r.name}': True})
            for r in [right for right in all_rights
                      if right.allow_read_rights_on_any_level
                      or right.allow_edit_rights_on_any_level]
        ])

    @classmethod
    def edit_on_any_level_query(cls, prefix: str = None) -> Q:
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{r.name}': True})
            for r in [right for right in all_rights
                      if right.allow_edit_rights_on_any_level]
        ])

    @property
    def right_groups(self) -> List[RightGroup]:
        def get_right_group(rg: RightGroup):
            res = []
            for r in map(lambda x: x.name, rg.rights):
                if getattr(self, r):
                    res.append(rg)
                    break
            return res + sum([get_right_group(c) for c in rg.children], [])

        if self._right_groups is None:
            self._right_groups = get_right_group(main_admin_rights)
        return self._right_groups

    def get_specific_readable_rights(
            self, getter: Callable[[RightGroup], List[Right]]) -> List[str]:
        res = []
        for rg in self.right_groups:
            for right in getter(rg):
                if getattr(self, right.name):
                    readable_rights = sum([[r.name for r in c.rights]
                                           for c in rg.children], [])
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
            self._inf_level_readable_rights = self.get_specific_readable_rights(
                lambda rg: rg.rights_read_on_inferior_levels
            )
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
            self._same_level_readable_rights = self.get_specific_readable_rights(
                lambda rg: rg.rights_read_on_same_level
            )
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
            if any(getattr(self, right.name)
                   for right in rg.rights_allowing_reading_accesses):
                for c in rg.children:
                    if len(c.children_rights):
                        not_true = dict((r.name, False) for r in c.rights)
                        rg_criteria.extend({r.name: True, **not_true}
                                           for r in c.children_rights)
                rg_criteria.extend({r.name: True} for r in rg.unreadable_rights)
                criteria = intersect_queryset_criteria(criteria, rg_criteria)

        return criteria

    @property
    def can_manage_other_accesses(self):
        return self.right_manage_admin_accesses_same_level \
               or self.right_manage_admin_accesses_inferior_levels \
               or self.right_manage_data_accesses_same_level \
               or self.right_manage_data_accesses_inferior_levels \
               or self.right_edit_roles \
               or self.right_manage_review_transfer_jupyter \
               or self.right_manage_transfer_jupyter \
               or self.right_manage_review_export_csv \
               or self.right_manage_export_csv

    @property
    def can_read_other_accesses(self):
        return self.right_edit_roles \
               or self.right_read_admin_accesses_same_level \
               or self.right_read_admin_accesses_inferior_levels \
               or self.right_read_data_accesses_same_level \
               or self.right_read_data_accesses_inferior_levels \
               or self.right_manage_review_transfer_jupyter \
               or self.right_manage_transfer_jupyter \
               or self.right_manage_review_export_csv \
               or self.right_manage_export_csv

    @property
    def requires_manage_review_export_csv_role(self):
        return any([
            self.right_review_export_csv,
        ])

    @property
    def requires_manage_export_csv_role(self):
        return any([
            self.right_export_csv_nominative,
            self.right_export_csv_pseudo_anonymised,
        ])

    @property
    def requires_manage_review_transfer_jupyter_role(self):
        return any([
            self.right_review_transfer_jupyter,
        ])

    @property
    def requires_manage_transfer_jupyter_role(self):
        return any([
            self.right_transfer_jupyter_nominative,
            self.right_transfer_jupyter_pseudo_anonymised,
        ])

    @property
    def requires_admin_role(self):
        return any([
            self.right_read_patient_nominative,
            self.right_search_patient_with_ipp,
            self.right_read_patient_pseudo_anonymised,
        ])

    @property
    def requires_admin_managing_role(self):
        return any([
            self.right_manage_data_accesses_same_level,
            self.right_read_data_accesses_same_level,
            self.right_manage_data_accesses_inferior_levels,
            self.right_read_data_accesses_inferior_levels,
            # self.data_accesses_types
        ])

    @property
    def requires_main_admin_role(self):
        return any([
            self.right_edit_roles,
            self.right_read_logs,
            self.right_add_users,
            self.right_edit_users,
            self.right_manage_admin_accesses_same_level,
            self.right_read_admin_accesses_same_level,
            self.right_manage_admin_accesses_inferior_levels,
            self.right_read_admin_accesses_inferior_levels,
            self.right_read_env_unix_users,
            self.right_manage_env_unix_users,
            self.right_manage_env_user_links,
            self.right_manage_review_transfer_jupyter,
            self.right_manage_transfer_jupyter,
            self.right_manage_review_export_csv,
            self.right_manage_export_csv,
        ])

    @property
    def requires_any_admin_mng_role(self):
        # to be managed, the role requires an access with
        # main admin or admin manager
        return any([
            self.right_read_users,
        ])

    @property
    def help_text(self):
        frs = []

        if self.right_edit_roles:
            frs.append("Gérer les rôles")
        if self.right_read_logs:
            frs.append("Lire l'historique des requêtes des utilisateurs")

        if self.right_add_users:
            frs.append("Ajouter un profil manuel "
                       "pour un utilisateur de l'AP-HP.")
        if self.right_edit_users:
            frs.append("Modifier les profils manuels, "
                       "et activer/désactiver les autres.")
        if self.right_read_users:
            frs.append("Consulter la liste des utilisateurs/profils")

        if self.right_manage_admin_accesses_same_level \
                and self.right_manage_admin_accesses_inferior_levels:
            frs.append("Gérer les accès des administrateurs "
                       "sur son périmètre et ses sous-périmètres")
        else:
            if self.right_manage_admin_accesses_same_level:
                frs.append("Gérer les accès des administrateurs "
                           "sur son périmètre exclusivement")
            if self.right_manage_admin_accesses_inferior_levels:
                frs.append("Gérer les accès des administrateurs "
                           "sur les sous-périmètres exclusivement")

        if self.right_read_admin_accesses_same_level \
                and self.right_read_admin_accesses_inferior_levels:
            frs.append("Consulter la liste des accès administrateurs "
                       "d'un périmètre et ses sous-périmètres")
        else:
            if self.right_read_admin_accesses_same_level:
                frs.append("Consulter la liste des "
                           "accès administrateurs d'un périmètre")
            if self.right_read_admin_accesses_inferior_levels:
                frs.append("Consulter la liste des accès administrateurs "
                           "des sous-périmètres")

        if self.right_manage_data_accesses_same_level \
                and self.right_manage_data_accesses_inferior_levels:
            frs.append("Gérer les accès aux données "
                       "sur son périmètre et ses sous-périmètres")
        else:
            if self.right_manage_data_accesses_same_level:
                frs.append("Gérer les accès aux données "
                           "sur son périmètre exclusivement")
            if self.right_manage_data_accesses_inferior_levels:
                frs.append("Gérer les accès aux données "
                           "sur les sous-périmètres exclusivement")

        if self.right_read_data_accesses_same_level \
                and self.right_read_data_accesses_inferior_levels:
            frs.append("Consulter la liste des accès aux données patients "
                       "d'un périmètre et ses sous-périmètres")
        else:
            if self.right_read_data_accesses_same_level:
                frs.append("Consulter la liste des accès aux "
                           "données patients d'un périmètre")
            if self.right_read_data_accesses_inferior_levels:
                frs.append("Consulter la liste des accès aux données "
                           "patients d'un sous-périmètre")

        if self.right_read_patient_nominative:
            frs.append("Lire les données patient sous forme nominatives "
                       "sur son périmètre et ses sous-périmètres")
        if self.right_search_patient_with_ipp:
            frs.append("Utiliser une liste d'IPP comme "
                       "critère d'une requête Cohort.")
        if self.right_read_patient_pseudo_anonymised:
            frs.append("Lire les données patient sous forme pseudonymisée "
                       "sur son périmètre et ses sous-périmètres")

        # JUPYTER TRANSFER
        if self.right_manage_review_transfer_jupyter:
            frs.append("Gérer les accès permettant de valider "
                       "ou non les demandes de "
                       "transfert de données vers des environnements Jupyter")

        if self.right_review_transfer_jupyter:
            frs.append("Gérer les transferts de données "
                       "vers des environnements Jupyter")

        if self.right_manage_transfer_jupyter:
            frs.append(
                "Gérer les accès permettant de réaliser des demandes de "
                "transfert de données vers des environnements Jupyter")

        if self.right_transfer_jupyter_nominative:
            frs.append("Demander à transférer ses cohortes de patients "
                       "sous forme nominative vers un environnement Jupyter.")
        if self.right_transfer_jupyter_pseudo_anonymised:
            frs.append(
                "Demander à transférer ses cohortes de patients sous "
                "forme pseudonymisée vers un environnement Jupyter.")

        # CSV EXPORT
        if self.right_manage_review_export_csv:
            frs.append("Gérer les accès permettant de valider ou non les "
                       "demandes d'export de données en format CSV")

        if self.right_review_export_csv:
            frs.append("Valider ou non les demandes d'export de données "
                       "en format CSV")

        if self.right_manage_export_csv:
            frs.append(
                "Gérer les accès permettant de réaliser des demandes "
                "d'export de données en format CSV")

        if self.right_export_csv_nominative:
            frs.append("Demander à exporter ses cohortes de patients"
                       " sous forme nominative en format CSV.")

        if self.right_export_csv_pseudo_anonymised:
            frs.append("Demander à exporter ses cohortes de patients sous "
                       "forme pseudonymisée en format CSV.")

        if self.right_read_env_unix_users:
            frs.append(
                "Consulter les informations liées aux environnements "
                "de travail")

        if self.right_manage_env_unix_users:
            frs.append("Gérer les environnements de travail")

        if self.right_manage_env_user_links:
            frs.append(
                "Gérer les accès des utilisateurs aux environnements "
                "de travail")

        return frs
