from datetime import date, timedelta, datetime
from typing import List, Dict, Union

from django.db.models import QuerySet, Q, Prefetch, F, Value
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accesses.models import Perimeter, Role, Access, Profile
from accesses.services.shared import DataRight
from admin_cohort.models import User
from admin_cohort.settings import ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS, PERIMETERS_TYPES, MANUAL_SOURCE, MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS
from admin_cohort.tools import join_qs


class AccessesService:

    @staticmethod
    def get_user_valid_accesses(user: User) -> QuerySet:
        return Access.objects.filter(Access.q_is_valid()
                                     & Profile.q_is_valid(prefix="profile")
                                     & Q(profile__source=MANUAL_SOURCE)
                                     & Q(profile__user=user))

    def user_is_full_admin(self, user: User) -> bool:
        return any(filter(lambda role: role.right_full_admin,
                          [access.role for access in self.get_user_valid_accesses(user)]))

    def user_has_data_reading_accesses(self, user: User) -> bool:
        return self.get_user_valid_accesses(user=user).filter(Role.q_allow_read_patient_data_nominative()
                                                              | Role.q_allow_read_patient_data_pseudo())\
                                                      .exists()

    @staticmethod
    def get_expiring_accesses(user: User, accesses: QuerySet):
        today = date.today()
        expiry_date = today + timedelta(days=ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
        to_expire_soon = Q(end_datetime__date__gte=today) & Q(end_datetime__date__lte=expiry_date)
        accesses_to_expire = accesses.filter(Q(profile__user=user) & to_expire_soon)
        if not accesses_to_expire:
            return None
        min_access_per_perimeter = {}
        for a in accesses_to_expire:
            if a.perimeter.id not in min_access_per_perimeter or \
                    a.end_datetime < min_access_per_perimeter[a.perimeter.id].end_datetime:
                min_access_per_perimeter[a.perimeter.id] = a
            else:
                continue
        return min_access_per_perimeter.values()

    def filter_accesses_for_user(self, user: User, accesses: QuerySet) -> QuerySet:
        """ filter the accesses, the user making the request, is allowed to see.
            return a filtered QuerySet of accesses annotated with "editable" set to True or False to indicate
            to Front whether to allow the `edit`/`close` actions on access or not
        """
        editable, readonly = [], []
        for access in accesses:
            if self.can_user_manage_access(user=user, target_access=access):
                editable.append(access.id)
            elif self.can_user_read_access(user=user, target_access=access):
                readonly.append(access.id)
        editable_accesses = accesses.filter(id__in=editable).annotate(editable=Value(True))
        readonly_accesses = accesses.filter(id__in=readonly).annotate(editable=Value(False))
        return editable_accesses.union(readonly_accesses)

    def get_accesses_on_perimeter(self, user: User, accesses: QuerySet, perimeter_id: int, include_parents: bool = False) -> QuerySet:
        q = Q(perimeter_id=perimeter_id)
        if include_parents:
            perimeter = Perimeter.objects.get(pk=perimeter_id)
            user_accesses = self.get_user_valid_accesses(user=user)
            user_can_read_accesses_from_above_levels = user_accesses.filter(role__right_read_accesses_above_levels=True) \
                                                                    .exists()
            if user_can_read_accesses_from_above_levels:
                q = q | (Q(perimeter_id__in=perimeter.above_levels)
                         & Role.q_impact_inferior_levels())
        return accesses.filter(Q(sql_is_valid=True) & q)
        # return self.filter_accesses_for_user(user=user, accesses=accesses_on_perimeter)                               # todo: check with the team

    @staticmethod
    def has_at_least_one_read_nominative_access(target_perimeters: QuerySet, nomi_perimeters_ids: List[int]) -> bool:
        for perimeter in target_perimeters:
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            if any(p_id in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
                return True
        return False

    def can_user_read_patient_data_in_nomi(self, user: User, target_perimeters: QuerySet) -> bool:
        user_accesses = self.get_user_valid_accesses(user=user)
        read_patient_data_nomi_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
        nomi_perimeters_ids = [access.perimeter_id for access in read_patient_data_nomi_accesses]
        allow_read_patient_data_nomi = self.has_at_least_one_read_nominative_access(target_perimeters=target_perimeters,
                                                                                    nomi_perimeters_ids=nomi_perimeters_ids)
        return allow_read_patient_data_nomi

    @staticmethod
    def user_has_at_least_one_pseudo_access_on_target_perimeters(target_perimeters: QuerySet,
                                                                 nomi_perimeters_ids: List[int],
                                                                 pseudo_perimeters_ids: List[int]) -> bool:
        for perimeter in target_perimeters:
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            if any(p_id in pseudo_perimeters_ids and p_id not in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
                return True

    @staticmethod
    def user_has_at_least_one_pseudo_access(nomi_perimeters_ids: List[int], pseudo_perimeters_ids: List[int]) -> bool:
        for perimeter in Perimeter.objects.filter(id__in=pseudo_perimeters_ids):
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            if all(p_id not in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
                return True
        return False

    def can_user_read_patient_data_in_pseudo(self, user: User, target_perimeters: QuerySet) -> bool:
        user_accesses = self.get_user_valid_accesses(user=user)
        read_patient_data_nomi_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
        read_patient_data_pseudo_accesses = user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                                 Role.q_allow_read_patient_data_nominative())

        nomi_perimeters_ids = [access.perimeter_id for access in read_patient_data_nomi_accesses]
        pseudo_perimeters_ids = [access.perimeter_id for access in read_patient_data_pseudo_accesses]

        if target_perimeters:
            allow_read_patient_data_pseudo = self.user_has_at_least_one_pseudo_access_on_target_perimeters(
                target_perimeters=target_perimeters,
                nomi_perimeters_ids=nomi_perimeters_ids,
                pseudo_perimeters_ids=pseudo_perimeters_ids)
        else:
            allow_read_patient_data_pseudo = self.user_has_at_least_one_pseudo_access(nomi_perimeters_ids=nomi_perimeters_ids,
                                                                                      pseudo_perimeters_ids=pseudo_perimeters_ids)
        return allow_read_patient_data_pseudo

    def can_user_read_opposed_patient_data(self, user: User) -> bool:
        user_accesses = self.get_user_valid_accesses(user=user)
        return user_accesses.filter(Role.q_allow_read_research_opposed_patient_data()).exists()

    def get_user_data_accesses(self, user: User) -> QuerySet:
        return self.get_user_valid_accesses(user).filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                  Q(role__right_read_patient_pseudonymized=True),
                                                                  Q(role__right_search_patients_by_ipp=True),
                                                                  Q(role__right_search_opposed_patients=True),
                                                                  Q(role__right_export_csv_nominative=True),
                                                                  Q(role__right_export_csv_pseudonymized=True),
                                                                  Q(role__right_export_jupyter_pseudonymized=True),
                                                                  Q(role__right_export_jupyter_nominative=True)]))

    def get_data_accesses_with_rights(self, user: User) -> QuerySet:
        return self.get_user_data_accesses(user).prefetch_related("role", "profile") \
                                            .prefetch_related(Prefetch('perimeter',
                                                                       queryset=Perimeter.objects.all().
                                                                       select_related(*["parent" + i * "__parent"
                                                                                        for i in range(0, len(PERIMETERS_TYPES) - 2)]))) \
                                            .annotate(right_read_patient_nominative=F('role__right_read_patient_nominative'),
                                                      right_read_patient_pseudonymized=F('role__right_read_patient_pseudonymized'),
                                                      right_search_patients_by_ipp=F('role__right_search_patients_by_ipp'),
                                                      right_search_opposed_patients=F('role__right_search_opposed_patients'),
                                                      right_export_csv_pseudonymized=F('role__right_export_csv_pseudonymized'),
                                                      right_export_csv_nominative=F('role__right_export_csv_nominative'),
                                                      right_export_jupyter_pseudonymized=F('role__right_export_jupyter_pseudonymized'),
                                                      right_export_jupyter_nominative=F('role__right_export_jupyter_nominative'))

    @staticmethod
    def get_data_rights_from_accesses(user: User, data_accesses: QuerySet) -> List[DataRight]:
        accesses_with_reading_patient_data_rights = data_accesses.filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                                  Q(role__right_read_patient_pseudonymized=True),
                                                                                  Q(role__right_search_patients_by_ipp=True),
                                                                                  Q(role__right_search_opposed_patients=True)]))
        return [DataRight(user_id=user.pk, perimeter=access.perimeter, reading_rights=access.__dict__)
                for access in accesses_with_reading_patient_data_rights]

    @staticmethod
    def get_data_rights_for_target_perimeters(user: User, target_perimeters: QuerySet) -> List[DataRight]:
        return [DataRight(user_id=user.pk, perimeter=perimeter, reading_rights=None)
                for perimeter in target_perimeters]

    @staticmethod
    def group_data_rights_by_perimeter(data_rights: List[DataRight]) -> Dict[int, DataRight]:
        data_rights_per_perimeter = {}
        for dr in data_rights:
            perimeter_id = dr.perimeter.id
            if perimeter_id not in data_rights_per_perimeter:
                data_rights_per_perimeter[perimeter_id] = dr
            else:
                data_rights_per_perimeter[perimeter_id].acquire_extra_data_reading_rights(dr=dr)
        return data_rights_per_perimeter

    @staticmethod
    def share_data_reading_rights_over_relative_hierarchy(data_rights_per_perimeter: Dict[int, DataRight]) -> List[DataRight]:
        processed_perimeters = []
        for perimeter_id, data_right in data_rights_per_perimeter.items():
            if perimeter_id in processed_perimeters:
                continue
            processed_perimeters.append(perimeter_id)
            parental_chain = [data_right]
            parent_perimeter = Perimeter.objects.get(pk=perimeter_id).parent
            while parent_perimeter:
                parent_data_right = data_rights_per_perimeter.get(parent_perimeter.id)
                if not parent_data_right:
                    parent_perimeter = parent_perimeter.parent
                    continue
                for dr in parental_chain:
                    dr.acquire_extra_data_reading_rights(dr=parent_data_right)
                parental_chain.append(parent_data_right)
                if parent_perimeter.id in processed_perimeters:
                    break
                processed_perimeters.append(parent_perimeter.id)
                parent_perimeter = parent_perimeter.parent
        return list(data_rights_per_perimeter.values())

    @staticmethod
    def share_global_rights_over_relative_hierarchy(user: User, data_rights: List[DataRight], data_accesses: QuerySet[Access]):
        for access in data_accesses.filter(join_qs([Q(role__right_export_csv_nominative=True),
                                                    Q(role__right_export_csv_pseudonymized=True),
                                                    Q(role__right_export_jupyter_nominative=True),
                                                    Q(role__right_export_jupyter_pseudonymized=True)])):
            global_dr = DataRight(user_id=user.pk,
                                  reading_rights=access.__dict__,
                                  perimeter=None)
            for dr in data_rights:
                dr.acquire_extra_global_rights(global_dr)

    def get_data_reading_rights(self, user: User, target_perimeters_ids: str) -> List[DataRight]:
        target_perimeters_ids = target_perimeters_ids and target_perimeters_ids.split(",") or []
        target_perimeters = Perimeter.objects.filter(id__in=target_perimeters_ids) \
                                             .select_related(*[f"parent{i * '__parent'}" for i in range(0, len(PERIMETERS_TYPES) - 2)])

        data_accesses = self.get_data_accesses_with_rights(user)
        data_rights_from_accesses = self.get_data_rights_from_accesses(user=user, data_accesses=data_accesses)
        data_rights_for_perimeters = []
        if target_perimeters:
            data_rights_for_perimeters = self.get_data_rights_for_target_perimeters(user=user,
                                                                                    target_perimeters=target_perimeters)
        data_rights_per_perimeter = self.group_data_rights_by_perimeter(data_rights=data_rights_from_accesses + data_rights_for_perimeters)

        data_rights = self.share_data_reading_rights_over_relative_hierarchy(data_rights_per_perimeter=data_rights_per_perimeter)

        self.share_global_rights_over_relative_hierarchy(user=user,
                                                         data_rights=data_rights,
                                                         data_accesses=data_accesses)
        if target_perimeters:
            data_rights = filter(lambda dr: dr.perimeter in target_perimeters, data_rights)

        return [dr for dr in data_rights if any((dr.right_read_patient_nominative,
                                                 dr.right_read_patient_pseudonymized,
                                                 dr.right_search_patients_by_ipp,
                                                 dr.right_search_opposed_patients))]

    def get_user_managing_accesses_on_perimeter(self, user: User, perimeter: Perimeter) -> QuerySet:
        """ filter user's valid accesses to extract:
              + those configured directly on the given perimeter AND allow to manage accesses on the same level
              + those configured on any of the perimeter's parents AND allow to manage accesses on inferior levels
              + those allowing to read/manage Exports accesses (global rights, allow to manage on any level)
        """
        return self.get_user_valid_accesses(user).filter((Q(perimeter=perimeter) & Role.q_allow_manage_accesses_on_same_level())
                                                         | (perimeter.q_all_parents() & Role.q_allow_manage_accesses_on_inf_levels())
                                                         | Role.q_allow_manage_export_accesses()) \
                                                 .distinct()\
                                                 .select_related("role")

    def get_user_reading_accesses_on_perimeter(self, user: User, perimeter: Perimeter) -> QuerySet:
        """ filter user's valid accesses to extract:
              + those configured directly on the given perimeter AND allow to read/manage accesses on the same level
              + those configured on any of the perimeter's parents AND allow to read/manage accesses on inferior levels
              + those allowing to read/manage Exports accesses (global rights, allow to manage on any level)
        """
        return self.get_user_valid_accesses(user).filter((Q(perimeter=perimeter) & Role.q_allow_read_accesses_on_same_level())
                                                         | (perimeter.q_all_parents() & Role.q_allow_read_accesses_on_inf_levels())
                                                         | Role.q_allow_manage_export_accesses()) \
                                                 .distinct() \
                                                 .select_related("role")

    @staticmethod
    def check_user_rights_on_perimeter(user_access: Access, target_perimeter: Perimeter, manage: False):
        role = user_access.role
        if target_perimeter == user_access.perimeter:
            right_on_admin_accesses = manage and role.right_manage_admin_accesses_same_level or role.right_read_admin_accesses_same_level
            right_on_data_accesses = manage and role.right_manage_data_accesses_same_level or role.right_read_data_accesses_same_level
        elif target_perimeter.is_child_of(perimeter=user_access.perimeter):
            right_on_admin_accesses = manage and role.right_manage_admin_accesses_inferior_levels or role.right_read_admin_accesses_inferior_levels
            right_on_data_accesses = manage and role.right_manage_data_accesses_inferior_levels or role.right_read_data_accesses_inferior_levels
        else:
            return False, False
        return right_on_admin_accesses, right_on_data_accesses

    def can_user_read_access(self, user: User, target_access: Access) -> bool:
        if self.user_is_full_admin(user):
            return True
        can_read_admin_accesses = False
        can_read_data_accesses = False
        can_read_export_csv_accesses = False
        can_read_export_jupyter_accesses = False

        access_perimeter = target_access.perimeter
        access_role = target_access.role

        user_accesses = self.get_user_reading_accesses_on_perimeter(user=user, perimeter=access_perimeter)

        for access in user_accesses:
            can_read_admin_accesses_2, can_read_data_accesses_2 = self.check_user_rights_on_perimeter(user_access=access,
                                                                                                      target_perimeter=access_perimeter,
                                                                                                      manage=False)
            can_read_admin_accesses = can_read_admin_accesses or can_read_admin_accesses_2
            can_read_data_accesses = can_read_data_accesses or can_read_data_accesses_2
            can_read_export_csv_accesses = can_read_export_csv_accesses or access.role.right_manage_export_csv_accesses
            can_read_export_jupyter_accesses = can_read_export_jupyter_accesses or access.role.right_manage_export_jupyter_accesses

        return not self.access_requires_full_admin_role_to_be_read(role=access_role) \
            and (can_read_admin_accesses or not self.access_requires_admin_accesses_reading_role_to_be_read(role=access_role)) \
            and (can_read_data_accesses or not self.access_requires_data_accesses_reading_role_to_be_read(role=access_role)) \
            and (can_read_export_csv_accesses or not self.access_requires_csv_accesses_reading_role_to_be_read(role=access_role)) \
            and (can_read_export_jupyter_accesses or not self.access_requires_jupyter_accesses_reading_role_to_be_read(role=access_role))

    def can_user_manage_access(self, user: User, target_access: Union[Access, dict]) -> bool:
        if self.user_is_full_admin(user):
            return True
        can_manage_admin_accesses = False
        can_manage_data_accesses = False
        can_manage_export_csv_accesses = False
        can_manage_export_jupyter_accesses = False

        access_perimeter = isinstance(target_access, Access) and target_access.perimeter or target_access.get('perimeter')
        access_role = isinstance(target_access, Access) and target_access.role or target_access.get('role')

        user_accesses = self.get_user_managing_accesses_on_perimeter(user=user, perimeter=access_perimeter)

        for access in user_accesses:
            can_manage_admin_accesses_2, can_manage_data_accesses_2 = self.check_user_rights_on_perimeter(user_access=access,
                                                                                                          target_perimeter=access_perimeter,
                                                                                                          manage=True)
            can_manage_admin_accesses = can_manage_admin_accesses or can_manage_admin_accesses_2
            can_manage_data_accesses = can_manage_data_accesses or can_manage_data_accesses_2
            can_manage_export_csv_accesses = can_manage_export_csv_accesses or access.role.right_manage_export_csv_accesses
            can_manage_export_jupyter_accesses = can_manage_export_jupyter_accesses or access.role.right_manage_export_jupyter_accesses

        return not self.access_requires_full_admin_role_to_be_managed(role=access_role) \
            and (can_manage_admin_accesses or not self.access_requires_admin_accesses_managing_role_to_be_managed(role=access_role)) \
            and (can_manage_data_accesses or not self.access_requires_data_accesses_managing_role_to_be_managed(role=access_role)) \
            and (can_manage_export_csv_accesses or not self.access_requires_csv_accesses_managing_role_to_be_managed(role=access_role)) \
            and (can_manage_export_jupyter_accesses or not self.access_requires_jupyter_accesses_managing_role_to_be_managed(role=access_role))

    def access_requires_full_admin_role_to_be_read(self, role: Role):
        return self.access_requires_full_admin_role_to_be_managed(role=role)

    def access_requires_admin_accesses_reading_role_to_be_read(self, role: Role):
        # requires having: right_read_admin_accesses_same/inf_level = True
        return self.access_requires_admin_accesses_managing_role_to_be_managed(role=role)

    def access_requires_data_accesses_reading_role_to_be_read(self, role: Role):
        # requires having: right_read_data_accesses_same/inf_level = True
        return self.access_requires_data_accesses_managing_role_to_be_managed(role=role)

    def access_requires_csv_accesses_reading_role_to_be_read(self, role: Role):
        return self.access_requires_csv_accesses_managing_role_to_be_managed(role=role)

    def access_requires_jupyter_accesses_reading_role_to_be_read(self, role: Role):
        return self.access_requires_jupyter_accesses_managing_role_to_be_managed(role=role)

    @staticmethod
    def access_requires_full_admin_role_to_be_managed(role: Role):
        # requires having: right_full_admin = True
        has_admin_accesses_role = any((role.right_manage_admin_accesses_same_level,
                                       role.right_manage_admin_accesses_inferior_levels,
                                       role.right_read_admin_accesses_same_level,
                                       role.right_read_admin_accesses_inferior_levels))
        return role.has_any_global_right() and has_admin_accesses_role

    @staticmethod
    def access_requires_admin_accesses_managing_role_to_be_managed(role: Role):
        # requires having: right_manage_admin_accesses_same/inf_level = True
        return any((role.right_manage_data_accesses_same_level,
                    role.right_manage_data_accesses_inferior_levels,
                    role.right_read_data_accesses_same_level,
                    role.right_read_data_accesses_inferior_levels))

    @staticmethod
    def access_requires_data_accesses_managing_role_to_be_managed(role: Role):
        # requires having: right_manage_data_accesses_same/inf_level = True
        return any((role.right_read_patient_nominative,
                    role.right_read_patient_pseudonymized))

    @staticmethod
    def access_requires_csv_accesses_managing_role_to_be_managed(role: Role):
        # requires having: right_manage_export_csv_accesses = True
        return any((role.right_export_csv_nominative,
                    role.right_export_csv_pseudonymized))

    @staticmethod
    def access_requires_jupyter_accesses_managing_role_to_be_managed(role: Role):
        # requires having: right_manage_export_jupyter_accesses = True
        return any((role.right_export_jupyter_nominative,
                    role.right_export_jupyter_pseudonymized))

    @staticmethod
    def check_access_closing_date(access: Access, end_datetime_now: datetime) -> None:
        if access.end_datetime < end_datetime_now:
            raise ValueError("L'accès est déjà clôturé")
        if access.start_datetime > end_datetime_now:
            raise ValueError("L'accès ne peut pas être clôturé car n'a pas encore commencé")

    def process_create_data(self, data: dict) -> None:
        start_datetime = data.get("start_datetime")
        end_datetime = data.get("end_datetime")

        data["start_datetime"] = start_datetime and parse_datetime(start_datetime) or timezone.now()
        data["end_datetime"] = (end_datetime and parse_datetime(end_datetime) or
                                data["start_datetime"] + timedelta(days=MIN_DEFAULT_END_DATE_OFFSET_IN_DAYS))
        self.check_access_dates(new_start_datetime=data["start_datetime"],
                                new_end_datetime=data["end_datetime"])

    def process_patch_data(self, access: Access, data: dict) -> None:
        if not data:
            raise ValueError("No data was provided to update access")

        updatable_fields = ("start_datetime", "end_datetime")
        if [k for k in data if k not in updatable_fields]:
            raise ValueError("Only `start_datetime` and `end_datetime` can be updated")

        start_datetime = data.get("start_datetime")
        end_datetime = data.get("end_datetime")

        if all(f in data for f in updatable_fields) and not (start_datetime and end_datetime):
            raise ValueError("Missing dates to updating access")

        start_datetime = start_datetime and parse_datetime(start_datetime) or None
        end_datetime = end_datetime and parse_datetime(end_datetime) or None
        self.check_access_dates(new_start_datetime=start_datetime,
                                new_end_datetime=end_datetime,
                                old_start_datetime=access.start_datetime,
                                old_end_datetime=access.end_datetime)

    @staticmethod
    def check_access_dates(new_start_datetime: datetime = None, new_end_datetime: datetime = None,
                           old_start_datetime: datetime = None, old_end_datetime: datetime = None) -> None:
        try:
            old_start_datetime = old_start_datetime and timezone.get_current_timezone().localize(old_start_datetime)
            old_end_datetime = old_end_datetime and timezone.get_current_timezone().localize(old_end_datetime)
        except ValueError:
            pass
        now = timezone.now()

        if old_start_datetime and new_start_datetime \
                and old_start_datetime != new_start_datetime \
                and old_start_datetime < now:
            raise ValueError("La date de début ne peut pas être modifiée car elle est passée")

        if old_end_datetime and new_end_datetime \
                and old_end_datetime != new_end_datetime \
                and old_end_datetime < now:
            raise ValueError("La date de fin ne peut pas être modifiée car elle est passée")

        if new_start_datetime and new_start_datetime + timedelta(seconds=10) < now:
            raise ValueError("La date de début ne peut pas être dans le passé")

        if new_end_datetime and new_end_datetime + timedelta(seconds=10) < now:
            raise ValueError("La date de fin ne peut pas être dans le passé")

        if new_start_datetime and new_end_datetime and new_end_datetime < new_start_datetime:
            raise ValueError("La date de fin ne peut pas précéder la date de début")


accesses_service = AccessesService()
