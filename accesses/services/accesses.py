import logging
from datetime import date, timedelta, datetime
from typing import List, Dict, Union, Literal

from django.db.models import QuerySet, Q, Prefetch, F, Value
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.conf import settings

from admin_cohort.models import User
from admin_cohort.tools import join_qs
from accesses.q_expressions import q_allow_read_search_opposed_patient_data, q_allow_read_patient_data_nominative, q_allow_read_patient_data_pseudo, \
    q_allow_manage_accesses_on_same_level, q_allow_manage_accesses_on_inf_levels, q_impact_inferior_levels, q_allow_unlimited_patients_search
from accesses.models import Perimeter, Access, Role
from accesses.services.shared import DataRight

_logger = logging.getLogger("info")


class AccessesService:

    @staticmethod
    def q_access_is_valid() -> Q:
        now = timezone.now()
        return Q(start_datetime__lte=now) & Q(end_datetime__gte=now)

    def get_user_valid_accesses(self, user: User) -> QuerySet:
        return Access.objects.filter(self.q_access_is_valid()
                                     & Q(profile__is_active=True)
                                     & Q(profile__user=user))

    def user_is_full_admin(self, user: User) -> bool:
        return any(filter(lambda role: role.right_full_admin,
                          [access.role for access in self.get_user_valid_accesses(user)]))

    @staticmethod
    def get_expiring_accesses(user: User, accesses: QuerySet):
        today = date.today()
        expiry_date = today + timedelta(days=settings.ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS)
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
            else:
                readonly.append(access.id)
        editable_accesses = accesses.filter(id__in=editable).annotate(editable=Value(True))
        readonly_accesses = accesses.filter(id__in=readonly).annotate(editable=Value(False))
        return editable_accesses.union(readonly_accesses)

    def get_accesses_on_perimeter(self,
                                  user: User,
                                  accesses: QuerySet,
                                  perimeter_id: int,
                                  include_parents: bool = False,
                                  include_children: bool = False) -> QuerySet:
        q = Q(perimeter_id=perimeter_id)
        perimeter = Perimeter.objects.get(pk=perimeter_id)
        user_accesses = self.get_user_valid_accesses(user=user)
        if include_parents:
            q = q | (Q(perimeter_id__in=perimeter.above_levels)
                     & q_impact_inferior_levels())
        if include_children:
            user_can_read_accesses_from_inferior_levels = user_accesses.filter(q_allow_manage_accesses_on_inf_levels()).exists()
            if user_can_read_accesses_from_inferior_levels:
                all_child_perimeters_ids = Perimeter.objects.filter(above_levels_ids__contains=perimeter_id) \
                                                        .values_list('id', flat=True)
                q = q | Q(perimeter_id__in=all_child_perimeters_ids)
        return self.filter_accesses_for_user(user=user, accesses=accesses.filter(q))

    def user_has_data_reading_accesses_on_target_perimeters(self, user: User,
                                                            target_perimeters: QuerySet,
                                                            read_mode: Literal["max", "min"]) -> bool:
        perimeters_with_data_accesses = self.get_user_valid_accesses(user=user)\
                                            .filter(q_allow_read_patient_data_nominative
                                                    | q_allow_read_patient_data_pseudo)\
                                            .values_list("perimeter_id", flat=True)
        if not perimeters_with_data_accesses:
            return False
        has_access = False
        for perimeter in target_perimeters:
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            can_access_perimeter = any(p in perimeters_with_data_accesses for p in perimeter_and_parents_ids)
            if read_mode == "max":
                if can_access_perimeter:
                    return True
            else:
                if not can_access_perimeter:
                    return False
                has_access = True
        return has_access

    def get_nominative_perimeters(self, user: User) -> QuerySet[int]:
        return self.get_user_valid_accesses(user=user)\
                   .filter(q_allow_read_patient_data_nominative)\
                   .values_list('perimeter_id', flat=True)

    def user_can_access_at_least_one_target_perimeter_in_nomi(self, user: User, target_perimeters: QuerySet) -> bool:
        nomi_perimeters_ids = self.get_nominative_perimeters(user=user)
        for perimeter in target_perimeters:
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            if any(p_id in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
                return True
        return False

    def user_can_access_all_target_perimeters_in_nomi(self, user: User, target_perimeters: QuerySet) -> bool:
        nomi_perimeters_ids = self.get_nominative_perimeters(user=user)
        for perimeter in target_perimeters:
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            if not any(p_id in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
                return False
        return True

    def can_user_read_opposed_patient_data(self, user: User) -> bool:
        return self.get_user_valid_accesses(user=user)\
                   .filter(q_allow_read_search_opposed_patient_data)\
                   .exists()

    def can_user_manage_users(self, user: User) -> bool:
        return self.get_user_valid_accesses(user=user)\
                   .filter(role__right_manage_users=True)\
                   .exists()

    def is_user_allowed_unlimited_patients_read(self, user: User) -> bool:
        return self.get_user_valid_accesses(user=user)\
                   .filter(q_allow_unlimited_patients_search)\
                   .exists()

    def get_user_data_accesses(self, user: User) -> QuerySet:
        return self.get_user_valid_accesses(user).filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                  Q(role__right_read_patient_pseudonymized=True),
                                                                  Q(role__right_search_patients_by_ipp=True),
                                                                  Q(role__right_search_opposed_patients=True),
                                                                  Q(role__right_export_csv_xlsx_nominative=True),
                                                                  Q(role__right_export_jupyter_pseudonymized=True),
                                                                  Q(role__right_export_jupyter_nominative=True)]))

    def get_data_accesses_with_rights(self, user: User) -> QuerySet:
        return self.get_user_data_accesses(user).prefetch_related("role", "profile") \
                                            .prefetch_related(Prefetch('perimeter',
                                                                       queryset=Perimeter.objects.all().
                                                                       select_related(*["parent" + i * "__parent"
                                                                                        for i in range(0, len(settings.PERIMETER_TYPES) - 2)]))) \
                                            .annotate(right_read_patient_nominative=F('role__right_read_patient_nominative'),
                                                      right_read_patient_pseudonymized=F('role__right_read_patient_pseudonymized'),
                                                      right_search_patients_by_ipp=F('role__right_search_patients_by_ipp'),
                                                      right_search_opposed_patients=F('role__right_search_opposed_patients'),
                                                      right_export_csv_xlsx_nominative=F('role__right_export_csv_xlsx_nominative'),
                                                      right_export_jupyter_pseudonymized=F('role__right_export_jupyter_pseudonymized'),
                                                      right_export_jupyter_nominative=F('role__right_export_jupyter_nominative'))

    @staticmethod
    def get_data_rights_from_accesses(user: User, data_accesses: QuerySet) -> List[DataRight]:
        accesses_with_reading_patient_data_rights = data_accesses.filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                                  Q(role__right_read_patient_pseudonymized=True)]))
        return [DataRight(user_id=user.pk,
                          perimeter_id=access.perimeter.id,
                          right_read_patient_nominative=access.right_read_patient_nominative,
                          right_read_patient_pseudonymized=access.right_read_patient_pseudonymized,
                          right_search_patients_by_ipp=access.right_search_patients_by_ipp,
                          right_search_opposed_patients=access.right_search_opposed_patients,
                          right_export_csv_xlsx_nominative=access.right_export_csv_xlsx_nominative,
                          right_export_jupyter_nominative=access.right_export_jupyter_nominative,
                          right_export_jupyter_pseudonymized=access.right_export_jupyter_pseudonymized)
                for access in accesses_with_reading_patient_data_rights]

    @staticmethod
    def get_data_rights_for_target_perimeters(user: User, target_perimeters_ids: List[int]) -> List[DataRight]:
        return [DataRight(user_id=user.pk, perimeter_id=perimeter_id)
                for perimeter_id in target_perimeters_ids]

    @staticmethod
    def group_data_rights_by_perimeter(data_rights: List[DataRight]) -> Dict[int, DataRight]:
        data_rights_per_perimeter = {}
        for dr in data_rights:
            perimeter_id = dr.perimeter_id
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
        for access in data_accesses.filter(join_qs([Q(role__right_search_patients_by_ipp=True),
                                                    Q(role__right_search_opposed_patients=True),
                                                    Q(role__right_export_csv_xlsx_nominative=True),
                                                    Q(role__right_export_jupyter_nominative=True),
                                                    Q(role__right_export_jupyter_pseudonymized=True)])):
            global_dr = DataRight(user_id=user.pk,
                                  perimeter_id=None,
                                  right_read_patient_nominative=access.right_read_patient_nominative,
                                  right_read_patient_pseudonymized=access.right_read_patient_pseudonymized,
                                  right_search_patients_by_ipp=access.right_search_patients_by_ipp,
                                  right_search_opposed_patients=access.right_search_opposed_patients,
                                  right_export_csv_xlsx_nominative=access.right_export_csv_xlsx_nominative,
                                  right_export_jupyter_nominative=access.right_export_jupyter_nominative,
                                  right_export_jupyter_pseudonymized=access.right_export_jupyter_pseudonymized)
            for dr in data_rights:
                dr.acquire_extra_global_rights(global_dr)

    def get_data_reading_rights(self, user: User, target_perimeters_ids: List[int]) -> List[DataRight]:
        target_perimeters = Perimeter.objects.filter(id__in=target_perimeters_ids) \
                                             .select_related(*[f"parent{i * '__parent'}" for i in range(0, len(settings.PERIMETER_TYPES) - 2)])

        data_accesses = self.get_data_accesses_with_rights(user)
        data_rights_from_accesses = self.get_data_rights_from_accesses(user=user, data_accesses=data_accesses)
        data_rights_for_perimeters = []
        if target_perimeters:
            data_rights_for_perimeters = self.get_data_rights_for_target_perimeters(user=user,
                                                                                    target_perimeters_ids=target_perimeters_ids)
        data_rights_per_perimeter = self.group_data_rights_by_perimeter(data_rights=data_rights_from_accesses + data_rights_for_perimeters)

        data_rights = self.share_data_reading_rights_over_relative_hierarchy(data_rights_per_perimeter=data_rights_per_perimeter)

        self.share_global_rights_over_relative_hierarchy(user=user,
                                                         data_rights=data_rights,
                                                         data_accesses=data_accesses)
        if target_perimeters:
            data_rights = filter(lambda dr: dr.perimeter_id in target_perimeters_ids, data_rights)

        return [dr for dr in data_rights if any((dr.right_read_patient_nominative,
                                                 dr.right_read_patient_pseudonymized))]

    def get_user_managing_accesses_on_perimeter(self, user: User, perimeter: Perimeter) -> QuerySet:
        """ filter user's valid accesses to extract:
              + those configured directly on the given perimeter AND allow to manage accesses on the same level
              + those configured on any of the perimeter's parents AND allow to manage accesses on inferior levels
              + those allowing to read/manage Exports accesses (global rights, allow to manage on any level)
        """
        return self.get_user_valid_accesses(user).filter((Q(perimeter=perimeter) & q_allow_manage_accesses_on_same_level())
                                                         | (perimeter.q_all_parents() & q_allow_manage_accesses_on_inf_levels())) \
                                                 .distinct() \
                                                 .select_related("role")

    @staticmethod
    def check_user_rights_on_perimeter(user_access: Access, target_perimeter: Perimeter):
        role = user_access.role
        if target_perimeter == user_access.perimeter:
            right_on_admin_accesses = role.right_manage_admin_accesses_same_level
            right_on_data_accesses = role.right_manage_data_accesses_same_level
        elif target_perimeter.is_child_of(perimeter=user_access.perimeter):
            right_on_admin_accesses = role.right_manage_admin_accesses_inferior_levels
            right_on_data_accesses = role.right_manage_data_accesses_inferior_levels
        else:
            return False, False
        return right_on_admin_accesses, right_on_data_accesses

    def can_user_manage_access(self, user: User, target_access: Union[Access, dict]) -> bool:
        if self.user_is_full_admin(user):
            return True

        can_manage_admin_accesses = False
        can_manage_data_accesses = False

        perimeter = target_access.perimeter if isinstance(target_access, Access) else target_access.get('perimeter')
        role = target_access.role if isinstance(target_access, Access) else target_access.get('role')

        role_requires_full_admin_right_to_be_managed = role.requires_full_admin_right_to_be_managed()
        role_requires_admin_accesses_managing_right_to_be_managed = role.requires_admin_accesses_managing_right_to_be_managed()
        role_requires_data_accesses_managing_right_to_be_managed = role.requires_data_accesses_managing_right_to_be_managed()


        user_accesses = self.get_user_managing_accesses_on_perimeter(user=user, perimeter=perimeter)

        for access in user_accesses:
            can_manage_admin_accesses_2, can_manage_data_accesses_2 = self.check_user_rights_on_perimeter(user_access=access,
                                                                                                          target_perimeter=perimeter)
            can_manage_admin_accesses = can_manage_admin_accesses or can_manage_admin_accesses_2
            can_manage_data_accesses = can_manage_data_accesses or can_manage_data_accesses_2 or can_manage_admin_accesses

        return not role_requires_full_admin_right_to_be_managed \
            and (can_manage_admin_accesses or not role_requires_admin_accesses_managing_right_to_be_managed) \
            and (can_manage_data_accesses or not role_requires_data_accesses_managing_right_to_be_managed)

    @staticmethod
    def role_requires_full_admin_right_to_be_read(role: Role):
        return role.requires_full_admin_right_to_be_managed()

    @staticmethod
    def role_requires_data_accesses_reading_right_to_be_read(role: Role):
        # requires having: right_read_data_accesses_same/inf_level = True
        return role.requires_data_accesses_managing_right_to_be_managed()

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
                                data["start_datetime"] + timedelta(days=settings.DEFAULT_ACCESS_VALIDITY_IN_DAYS))
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

    @staticmethod
    def close_accesses(perimeters_to_delete: QuerySet):
        perimeters_to_delete_ids = perimeters_to_delete.values_list("id", flat=True)
        accesses_to_delete = Access.objects.filter(accesses_service.q_access_is_valid()
                                                   & (Q(perimeter_id__in=perimeters_to_delete_ids) | Q(perimeter_id__isnull=True)))
        accesses_to_delete.update(end_datetime=timezone.now())
        _logger.info(f"{len(accesses_to_delete)} accesses have been closed: {accesses_to_delete}")


accesses_service = AccessesService()
