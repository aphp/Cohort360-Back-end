from __future__ import annotations
from typing import List, Dict, Union, Callable

from django.db import models
from django.db.models import CASCADE, Q, SET_NULL
from django.db.models.query import QuerySet, Prefetch
from django.utils import timezone
from django.utils.datetime_safe import datetime

from accesses.rights import RightGroup, main_admin_rights, all_rights, Right
from admin_cohort.models import BaseModel, User
from admin_cohort.settings import MANUAL_SOURCE, \
    PERIMETERS_TYPES
from admin_cohort.tools import join_qs

ADMIN_ROLE_ID = 0
ADMIN_USERS_ROLE_ID = 1
READ_DATA_PSEUDOANONYMISED_ROLE_ID = 2
READ_DATA_NOMINATIVE_ROLE_ID = 3
KNOWN_ROLES_IDS = [
    ADMIN_ROLE_ID, ADMIN_USERS_ROLE_ID,
    READ_DATA_PSEUDOANONYMISED_ROLE_ID, READ_DATA_NOMINATIVE_ROLE_ID
]


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


class Profile(BaseModel):
    id = models.AutoField(blank=True, null=False, primary_key=True)
    provider_id = models.BigIntegerField(blank=True, null=True)
    provider_name = models.TextField(blank=True, null=True)
    firstname = models.TextField(blank=True, null=True)
    lastname = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)

    is_active = models.BooleanField(blank=True, null=True)
    manual_is_active = models.BooleanField(blank=True, null=True)
    valid_start_datetime: datetime = models.DateTimeField(blank=True,
                                                          null=True)
    manual_valid_start_datetime: datetime = models.DateTimeField(
        blank=True, null=True)
    valid_end_datetime: datetime = models.DateTimeField(blank=True,
                                                        null=True)
    manual_valid_end_datetime: datetime = models.DateTimeField(
        blank=True, null=True)

    user = models.ForeignKey(User, on_delete=CASCADE,
                             related_name='profiles',
                             null=True, blank=True)

    class Meta:
        managed = True

    @property
    def is_valid(self):
        now = datetime.now().replace(tzinfo=None)
        if self.actual_valid_start_datetime is not None:
            if self.actual_valid_start_datetime.replace(tzinfo=None) > now:
                return False
        if self.actual_valid_end_datetime is not None:
            if self.actual_valid_end_datetime.replace(tzinfo=None) <= now:
                return False
        return self.actual_is_active

    @property
    def actual_is_active(self):
        return self.is_active if self.manual_is_active is None \
            else self.manual_is_active

    @property
    def actual_valid_start_datetime(self) -> datetime:
        return self.valid_start_datetime \
            if self.manual_valid_start_datetime is None \
            else self.manual_valid_start_datetime

    @property
    def actual_valid_end_datetime(self) -> datetime:
        return self.valid_end_datetime \
            if self.manual_valid_end_datetime is None \
            else self.manual_valid_end_datetime

    @property
    def cdm_source(self) -> str:
        return str(self.source)

    @classmethod
    def Q_is_valid(cls, field_prefix: str = '') -> Q:
        """
        Returns a query Q on Profile fields (can go with a prefix)
        Filtering on validity :
        - (valid_start or manual_valid_start if exist) is before now or null
        - (valid_end or manual_valid_end if exist) is after now or null
        - (active or manual_active if exist) is True
        :param field_prefix: str set before each field in case the queryset is
        used when Profile is a related object
        :return:
        """
        # now = datetime.now().replace(tzinfo=None)
        now = timezone.now()
        fields = dict(
            valid_start=f"{field_prefix}valid_start_datetime",
            manual_valid_start=f"{field_prefix}manual_valid_start_datetime",
            valid_end=f"{field_prefix}valid_end_datetime",
            manual_valid_end=f"{field_prefix}manual_valid_end_datetime",
            active=f"{field_prefix}is_active",
            manual_active=f"{field_prefix}manual_is_active",
        )
        q_actual_start_is_none = Q(**{
            fields['valid_start']: None,
            fields['manual_valid_start']: None
        })
        q_start_lte_now = ((Q(**{fields['manual_valid_start']: None})
                            & Q(**{f"{fields['valid_start']}__lte": now}))
                           | Q(
                    **{f"{fields['manual_valid_start']}__lte": now}))

        q_actual_end_is_none = Q(**{
            fields['valid_end']: None,
            fields['manual_valid_end']: None
        })
        q_end_gte_now = ((Q(**{fields['manual_valid_end']: None})
                          & Q(**{f"{fields['valid_end']}__gte": now}))
                         | Q(**{f"{fields['manual_valid_end']}__gte": now}))

        q_is_active = ((Q(**{fields['manual_active']: None})
                        & Q(**{fields['active']: True}))
                       | Q(**{fields['manual_active']: True}))
        return ((q_actual_start_is_none | q_start_lte_now)
                & (q_actual_end_is_none | q_end_gte_now)
                & q_is_active)


class Perimeter(BaseModel):
    id = models.BigAutoField(primary_key=True)
    local_id = models.CharField(max_length=63, unique=True)
    name = models.TextField(blank=True, null=True)
    source_value = models.TextField(blank=True, null=True)
    short_name = models.TextField(blank=True, null=True)
    type_source_value = models.TextField(blank=True, null=True)
    parent = models.ForeignKey("accesses.perimeter",
                               on_delete=models.CASCADE,
                               related_name="children", null=True)

    @property
    def names(self):
        return dict(name=self.name, short=self.short_name,
                    source_value=self.source_value)

    @property
    def type(self):
        return self.type_source_value

    @property
    def all_children_query(self) -> Q:
        return join_qs([Q(
            **{"__".join(i * ["parent"]): self}
        ) for i in range(1, len(PERIMETERS_TYPES))])

    @property
    def all_children_queryset(self) -> QuerySet:
        return Perimeter.objects.filter(self.all_children_query)

    def all_parents_query(self, prefix: str = None) -> Q:
        prefix = f"{prefix}__" if prefix is not None else ""
        return join_qs([
            Q(**{f'{prefix}{"__".join(i * ["children"])}': self})
            for i in range(1, len(PERIMETERS_TYPES))
        ])

    @property
    def all_parents_queryset(self) -> QuerySet:
        return Perimeter.objects.filter(self.all_parents_query()).distinct()

    @classmethod
    def children_prefetch(cls, filtered_queryset: QuerySet = None) -> Prefetch:
        """
        Returns a Prefetch taht can be given to a queryset.prefetch_related
        method to prefetch children and set results to 'prefetched_children'
        :param filtered_queryset: queryset on which filter the result
        of the prefetch
        :return:
        """
        filtered_queryset = filtered_queryset or cls.objects.all()
        return Prefetch('children', queryset=filtered_queryset,
                        to_attr='prefetched_children')

    class Meta:
        managed = True


def get_all_perimeters_parents_queryset(perims: List[Perimeter], ) -> QuerySet:
    return Perimeter.objects.filter(join_qs([
        p.all_parents_query() for p in perims
    ]))


def get_all_level_children(
        perimeters_ids: Union[int, List[int]], strict: bool = False,
        filtered_ids: List[str] = [], ids_only: bool = False
) -> List[Union[Perimeter, str]]:
    qs = join_qs(
        [Perimeter.objects.filter(
            **{i * 'parent__' + 'id__in': perimeters_ids}
        ) for i in range(0 + strict, len(PERIMETERS_TYPES))]
    )
    if len(filtered_ids):
        return qs.filter(id__in=filtered_ids)

    if ids_only:
        return [str(i[0]) for i in qs.values_list('id')]
    return list(qs)


def intersect_queryset_criteria(
        cs_a: List[Dict], cs_b: List[Dict]) -> List[Dict]:
    """
    Given two lists of Role Queryset criteria
    We keep only items that are in both lists
    Item is in both lists if it has the same
    'True' factors (ex.: right_edit_roles=True)
    If an item is in both, we merge the two versions :
    - with keeping 'False' factors,
    - with extending 'perimeter_not' and 'perimeter_not_child' lists
    :param cs_a:
    :param cs_b:
    :return:
    """
    res = []
    for c_a in cs_a:
        if c_a in cs_b:
            res.append(c_a)
        else:
            add = False
            for c_b in cs_b:
                none_perimeter_criteria = [
                    k for (k, v) in c_a.items()
                    if v and 'perimeter' not in k]
                if all(c_b.get(r) for r in none_perimeter_criteria):
                    add = True
                    perimeter_not = c_b.get('perimeter_not', [])
                    perimeter_not.extend(c_a.get('perimeter_not', []))
                    perimeter_not_child = c_b.get('perimeter_not_child',
                                                  [])
                    perimeter_not_child.extend(
                        c_a.get('perimeter_not_child', []))
                    if len(perimeter_not):
                        c_b['perimeter_not'] = perimeter_not
                    if len(perimeter_not_child):
                        c_b['perimeter_not_child'] = perimeter_not_child
                    c_a.update(c_b)
            if add:
                res.append(c_a)
    return res


class Access(BaseModel):
    id = models.BigAutoField(primary_key=True)
    perimeter = models.ForeignKey(
        Perimeter, to_field='id', on_delete=SET_NULL,
        related_name='accesses', null=True)
    source = models.TextField(blank=True, null=True, default=MANUAL_SOURCE)

    start_datetime = models.DateTimeField(blank=True, null=True)
    end_datetime = models.DateTimeField(blank=True, null=True)
    manual_start_datetime = models.DateTimeField(blank=True, null=True)
    manual_end_datetime = models.DateTimeField(blank=True, null=True)

    profile = models.ForeignKey(Profile, on_delete=CASCADE,
                                related_name='accesses', null=True)
    role: Role = models.ForeignKey(Role, on_delete=CASCADE,
                                   related_name='accesses', null=True)

    @property
    def is_valid(self):
        today = datetime.now()
        if self.actual_start_datetime is not None:
            actual_start_datetime = datetime.combine(
                self.actual_start_datetime.date()
                if isinstance(self.actual_start_datetime, datetime) else
                self.actual_start_datetime,
                datetime.min
            )
            if actual_start_datetime > today:
                return False
        if self.actual_end_datetime is not None:
            actual_end_datetime = datetime.combine(
                self.actual_end_datetime.date()
                if isinstance(self.actual_end_datetime, datetime)
                else self.actual_end_datetime,
                datetime.min
            )
            if actual_end_datetime <= today:
                return False
        return True

    @classmethod
    def Q_is_valid(cls) -> Q:
        # now = datetime.now().replace(tzinfo=None)
        now = timezone.now()
        q_actual_start_is_none = Q(start_datetime=None,
                                   manual_start_datetime=None)
        q_start_lte_now = ((Q(manual_start_datetime=None)
                            & Q(start_datetime__lte=now))
                           | Q(manual_start_datetime__lte=now))

        q_actual_end_is_none = Q(end_datetime=None,
                                 manual_end_datetime=None)
        q_end_gte_now = ((Q(manual_end_datetime=None)
                          & Q(end_datetime__gte=now))
                         | Q(manual_end_datetime__gte=now))
        return ((q_actual_start_is_none | q_start_lte_now)
                & (q_actual_end_is_none | q_end_gte_now))

    @property
    def care_site_id(self):
        return self.perimeter.id

    @property
    def care_site(self):
        return {
            'care_site_id': self.perimeter.id,
            'care_site_name': self.perimeter.name,
            'care_site_short_name': self.perimeter.short_name,
            'care_site_type_source_value': self.perimeter.type_source_value,
            'care_site_source_value': self.perimeter.source_value,
        } if self.perimeter else None

    @property
    def actual_start_datetime(self):
        return self.start_datetime if self.manual_start_datetime is None \
            else self.manual_start_datetime

    @property
    def actual_end_datetime(self):
        return self.end_datetime if self.manual_end_datetime is None \
            else self.manual_end_datetime

    @property
    def accesses_criteria_to_exclude(self) -> List[Dict]:
        res = self.role.unreadable_rights

        for read_r in (self.role.inf_level_readable_rights
                       + self.role.same_level_readable_rights):
            d = {read_r: True}

            if read_r in self.role.inf_level_readable_rights:
                d['perimeter_not_child'] = [self.perimeter_id]

            if read_r in self.role.same_level_readable_rights:
                d['perimeter_not'] = [self.perimeter_id]

            res.append(d)

        return res

    class Meta:
        managed = True


def can_roles_manage_access(
        user_accesses: List[Access], access_role: Role,
        perimeter: Perimeter, just_read: bool = False
) -> bool:
    """
    Given accesses from a user (perimeter + role), will determine if the user
    has specific rights to manage or read on other accesses,
    either on the perimeter or ones from inferior levels
    Then, depending on what the role requires to be managed,
    or read if just_read=True, will return if the accesses are sufficient
    @param user_accesses:
    @param access_role:
    @param perimeter_id:
    @param just_read: True if we should check the possibility to read, instea of
    to manage
    @return:
    """
    has_main_admin_role = any([acc.role.right_edit_roles
                               for acc in user_accesses])

    has_admin_managing_role = any(
        (
                (
                        (
                            acc.role.right_read_admin_accesses_same_level
                            if just_read
                            else acc.role.right_manage_admin_accesses_same_level
                        ) and acc.perimeter_id == perimeter.id
                ) or (
                        (acc.role.right_read_admin_accesses_inferior_levels
                         if just_read else
                         acc.role.right_manage_admin_accesses_inferior_levels
                         ) and acc.perimeter_id != perimeter.id
                )
        ) for acc in user_accesses

    )

    has_admin_role = any(
        (
                (
                        (
                            acc.role.right_read_data_accesses_same_level
                            if just_read
                            else acc.role.right_manage_data_accesses_same_level
                        ) and acc.perimeter_id == perimeter.id
                ) or (
                        (
                            acc.role.right_read_data_accesses_inferior_levels
                            if just_read else
                            acc.role.right_manage_data_accesses_inferior_levels
                        ) and acc.perimeter_id != perimeter.id
                )
        ) for acc in user_accesses
    )

    has_jupy_rvw_mng_role = any([
        acc.role.right_manage_review_transfer_jupyter for acc in user_accesses
    ])
    has_jupy_mng_role = any([
        acc.role.right_manage_transfer_jupyter for acc in user_accesses
    ])
    has_csv_rvw_mng_role = any([
        acc.role.right_manage_review_export_csv for acc in user_accesses
    ])
    has_csv_mng_role = any([
        acc.role.right_manage_export_csv for acc in user_accesses
    ])

    return (
                   not access_role.requires_main_admin_role
                   or has_main_admin_role
           ) and (
                   not access_role.requires_admin_managing_role
                   or has_admin_managing_role
           ) and (
                   not access_role.requires_admin_role
                   or has_admin_role
           ) and (
                   not access_role.requires_any_admin_mng_role
                   or has_main_admin_role or has_admin_managing_role
           ) and (
                   not access_role.requires_manage_review_transfer_jupyter_role
                   or has_jupy_rvw_mng_role
           ) and (
                   not access_role.requires_manage_transfer_jupyter_role
                   or has_jupy_mng_role
           ) and (
                   not access_role.requires_manage_review_export_csv_role
                   or has_csv_rvw_mng_role
           ) and (
                   not access_role.requires_manage_export_csv_role
                   or has_csv_mng_role
           )


def get_assignable_roles_on_perimeter(
        user: User, perimeter: Perimeter
) -> List[Role]:
    user_accesses = get_all_user_managing_accesses_on_perimeter(user, perimeter)
    return [
        r for r in Role.objects.all()
        if can_roles_manage_access(list(user_accesses), r, perimeter)
    ]


def get_all_user_managing_accesses_on_perimeter(
        user: User, perim: Perimeter
) -> QuerySet:
    """
    more than getting the access on one Perimeter
    will also get the ones from the other perimeters that contain this perimeter
    Perimeters are organised like a tree, perimeters contain other perimeters,
    and roles are thus inherited
    :param user:
    :param perimeter_id:
    :return:
    """

    return get_user_valid_manual_accesses_queryset(user).filter(
        (
                perim.all_parents_query("perimeter")
                & Role.manage_on_lower_levels_query("role")
        ) | (
                Q(perimeter=perim)
                & Role.manage_on_same_level_query("role")
        ) | Role.manage_on_any_level_query("role")).select_related("role")


def get_user_valid_manual_accesses_queryset(u: User) -> QuerySet:
    return Access.objects.filter(
        Profile.Q_is_valid(field_prefix="profile__")
        & Q(profile__source=MANUAL_SOURCE)
        & Access.Q_is_valid()
        & Q(profile__user=u)
    )


def get_user_data_accesses_queryset(u: User) -> QuerySet:
    return get_user_valid_manual_accesses_queryset(u).filter(
        join_qs(
            [Q(role__right_read_patient_nominative=True),
             Q(role__right_read_patient_pseudo_anonymised=True),
             Q(role__right_search_patient_with_ipp=True),
             Q(role__right_export_csv_nominative=True),
             Q(role__right_export_csv_pseudo_anonymised=True),
             Q(role__right_transfer_jupyter_pseudo_anonymised=True),
             Q(role__right_transfer_jupyter_nominative=True)]
        )).prefetch_related('role')


class DataRight:
    def __init__(self, perimeter_id: int, user_id: str, provider_id: int,
                 acc_ids: List[int] = None,
                 pseudo: bool = False, nomi: bool = False,
                 exp_pseudo: bool = False, exp_nomi: bool = False,
                 jupy_pseudo: bool = False, jupy_nomi: bool = False,
                 search_ipp: bool = False, **kwargs) -> Dict:
        """
        @return: a default DataRight as required by the serializer
        """
        if 'perimeter' in kwargs:
            self.perimeter: Perimeter = kwargs['perimeter']
        self.perimeter_id = perimeter_id
        self.provider_id = provider_id
        self.user_id = user_id
        self.access_ids = acc_ids or []
        self.right_read_patient_nominative = nomi
        self.right_read_patient_pseudo_anonymised = pseudo
        self.right_search_patient_with_ipp = search_ipp
        self.right_export_csv_nominative = exp_nomi
        self.right_export_csv_pseudo_anonymised = exp_pseudo
        self.right_transfer_jupyter_nominative = jupy_nomi
        self.right_transfer_jupyter_pseudo_anonymised = jupy_pseudo

    @property
    def rights_granted(self) -> List[str]:
        return [r for r in [
            'right_read_patient_nominative',
            'right_read_patient_pseudo_anonymised',
            'right_search_patient_with_ipp',
        ] if getattr(self, r)]

    @property
    def count_rights_granted(self) -> int:
        return len(self.rights_granted)

    def add_right(self, right: DataRight):
        """
        Adds a new DataRight access id to self access_ids
        and grants new rights given by this new DataRight
        :param right: other DataRight to complete with
        :return:
        """
        self.access_ids = list(set(
            self.access_ids + right.access_ids))
        self.right_read_patient_nominative = \
            self.right_read_patient_nominative \
            or right.right_read_patient_nominative
        self.right_read_patient_pseudo_anonymised = \
            self.right_read_patient_pseudo_anonymised \
            or right.right_read_patient_pseudo_anonymised
        self.right_search_patient_with_ipp = \
            self.right_search_patient_with_ipp \
            or right.right_search_patient_with_ipp

    def add_global_right(self, right: DataRight):
        """
        Adds a new DataRight access id to self access_ids
        and grants new rights given by this new DataRight
        :param right: other DataRight to complete with
        :return:
        """
        self.access_ids = list(set(
            self.access_ids + right.access_ids))
        self.right_export_csv_nominative = \
            self.right_export_csv_nominative \
            or right.right_export_csv_nominative
        self.right_export_csv_pseudo_anonymised = \
            self.right_export_csv_pseudo_anonymised \
            or right.right_export_csv_pseudo_anonymised
        self.right_transfer_jupyter_nominative = \
            self.right_transfer_jupyter_nominative \
            or right.right_transfer_jupyter_nominative
        self.right_transfer_jupyter_pseudo_anonymised = \
            self.right_transfer_jupyter_pseudo_anonymised \
            or right.right_transfer_jupyter_pseudo_anonymised

    def add_access_ids(self, ids: List[int]):
        self.access_ids = list(set(self.access_ids + ids))

    @property
    def has_data_read_right(self):
        return self.right_read_patient_nominative \
               or self.right_read_patient_pseudo_anonymised \
               or self.right_search_patient_with_ipp

    @property
    def has_global_data_right(self):
        return self.right_export_csv_nominative \
               or self.right_export_csv_pseudo_anonymised \
               or self.right_transfer_jupyter_nominative \
               or self.right_transfer_jupyter_pseudo_anonymised

    @property
    def care_site_history_ids(self) -> List[int]:
        return self.access_ids

    @property
    def care_site_id(self) -> int:
        return int(self.perimeter_id)
