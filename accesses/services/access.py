import urllib
from datetime import date, timedelta
from typing import List, Dict

from django.db.models import QuerySet, Q, Prefetch, F

from accesses.models import Perimeter, Role, Access, Profile
from accesses.services.shared import DataRight
from admin_cohort.models import User
from admin_cohort.settings import ACCESS_EXPIRY_FIRST_ALERT_IN_DAYS, PERIMETERS_TYPES, MANUAL_SOURCE
from admin_cohort.tools import join_qs


class AccessesService:

    @staticmethod
    def get_user_valid_manual_accesses(user: User) -> QuerySet:
        return Access.objects.filter(Access.q_is_valid()
                                     & Profile.q_is_valid(prefix="profile")
                                     & Q(profile__source=MANUAL_SOURCE)
                                     & Q(profile__user=user))

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
        for access in accesses:
            if self.can_user_manage_role_on_perimeter(user=user, target_role=access.role, target_perimeter=access.perimeter):
                access.editable = True
            elif self.can_user_read_role_on_perimeter(user=user, target_role=access.role, target_perimeter=access.perimeter):
                access.editable = False
            else:
                accesses = accesses.exclude(id=access.id)
        return accesses

    def get_accesses_on_perimeter(self, user: User, accesses: QuerySet, perimeter_id: int, include_parents: bool = False) -> QuerySet:
        valid_accesses = accesses.filter(sql_is_valid=True)
        accesses_on_perimeter = valid_accesses.filter(perimeter_id=perimeter_id)
        if include_parents:
            perimeter = Perimeter.objects.get(pk=perimeter_id)
            user_accesses = self.get_user_valid_manual_accesses(user=user)
            user_can_read_accesses_from_above_levels = user_accesses.filter(role__right_read_accesses_above_levels=True) \
                                                                    .exists()
            if user_can_read_accesses_from_above_levels:
                accesses_on_parent_perimeters = valid_accesses.filter(Q(perimeter_id__in=perimeter.above_levels)
                                                                      & Role.q_impact_inferior_levels())
                accesses_on_perimeter = accesses_on_perimeter.union(accesses_on_parent_perimeters)
        return self.filter_accesses_for_user(user=user, accesses=accesses_on_perimeter)

    @staticmethod
    def has_at_least_one_read_nominative_access(target_perimeters: QuerySet, nomi_perimeters_ids: List[int]) -> bool:
        for perimeter in target_perimeters:
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            if any(p_id in nomi_perimeters_ids for p_id in perimeter_and_parents_ids):
                return True
        return False

    def can_user_read_patient_data_in_nomi(self, user: User, target_perimeters: QuerySet) -> bool:
        user_accesses = self.get_user_valid_manual_accesses(user=user)
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
        user_accesses = self.get_user_valid_manual_accesses(user=user)
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
        user_accesses = self.get_user_valid_manual_accesses(user=user)
        return user_accesses.filter(Role.q_allow_read_research_opposed_patient_data()).exists()

    def get_user_data_accesses(self, user: User) -> QuerySet:
        return self.get_user_valid_manual_accesses(user).filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                         Q(role__right_read_patient_pseudonymized=True),
                                                                         Q(role__right_search_patients_by_ipp=True),
                                                                         Q(role__right_read_research_opposed_patient_data=True),
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
                                                      right_read_research_opposed_patient_data=F('role__right_read_research_opposed_patient_data'),
                                                      right_export_csv_pseudonymized=F('role__right_export_csv_pseudonymized'),
                                                      right_export_csv_nominative=F('role__right_export_csv_nominative'),
                                                      right_export_jupyter_pseudonymized=F('role__right_export_jupyter_pseudonymized'),
                                                      right_export_jupyter_nominative=F('role__right_export_jupyter_nominative'))

    @staticmethod
    def get_data_rights_from_accesses(user: User, data_accesses: QuerySet) -> List[DataRight]:
        accesses_with_reading_patient_data_rights = data_accesses.filter(join_qs([Q(role__right_read_patient_nominative=True),
                                                                                  Q(role__right_read_patient_pseudonymized=True),
                                                                                  Q(role__right_search_patients_by_ipp=True),
                                                                                  Q(role__right_read_research_opposed_patient_data=True)]))
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
        target_perimeters_ids and target_perimeters_ids.split(",") or []
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
                                                 dr.right_read_research_opposed_patient_data))]

    def get_user_managing_accesses_on_perimeter(self, user: User, perimeter: Perimeter) -> QuerySet:
        """ filter user's valid accesses to extract:
              + those configured directly on the given perimeter AND allow to manage accesses on the same level
              + those configured on any of the perimeter's parents AND allow to manage accesses on inferior levels
              + those allowing to read/manage Exports accesses (global rights, allow to manage on any level)
        """
        return self.get_user_valid_manual_accesses(user).filter((Q(perimeter=perimeter) & Role.q_allow_manage_accesses_on_same_level())
                                                                | (perimeter.q_all_parents() & Role.q_allow_manage_accesses_on_inf_levels())
                                                                | Role.q_allow_manage_export_accesses()) \
                                                        .select_related("role")

    def get_user_reading_accesses_on_perimeter(self, user: User, perimeter: Perimeter) -> QuerySet:
        """ filter user's valid accesses to extract:
              + those configured directly on the given perimeter AND allow to read/manage accesses on the same level
              + those configured on any of the perimeter's parents AND allow to read/manage accesses on inferior levels
              + those allowing to read/manage Exports accesses (global rights, allow to manage on any level)
        """
        return self.get_user_valid_manual_accesses(user).filter((Q(perimeter=perimeter) & Role.q_allow_read_accesses_on_same_level())
                                                                | (perimeter.q_all_parents() & Role.q_allow_read_accesses_on_inf_levels())
                                                                | Role.q_allow_manage_export_accesses()) \
                                                        .select_related("role")

    def can_user_read_role_on_perimeter(self, user: User, target_role: Role, target_perimeter: Perimeter) -> bool:
        return self.can_user_manage_role_on_perimeter(user=user,
                                                      target_role=target_role,
                                                      target_perimeter=target_perimeter,
                                                      readonly=True)

    @staticmethod
    def check_accesses_managing_roles_on_perimeter(access: Access, target_perimeter: Perimeter, readonly: bool):
        role = access.role
        if access.perimeter == target_perimeter:
            has_admin_accesses_managing_role = readonly and role.right_read_admin_accesses_same_level or role.right_manage_admin_accesses_same_level
            has_data_accesses_managing_role = readonly and role.right_read_data_accesses_same_level or role.right_manage_data_accesses_same_level
        elif target_perimeter.is_child_of(perimeter=access.perimeter):
            has_admin_accesses_managing_role = (readonly and role.right_read_admin_accesses_inferior_levels
                                                or role.right_manage_admin_accesses_inferior_levels)
            has_data_accesses_managing_role = (readonly and role.right_read_data_accesses_inferior_levels
                                               or role.right_manage_data_accesses_inferior_levels)
        else:
            has_admin_accesses_managing_role = False
            has_data_accesses_managing_role = False
        return has_admin_accesses_managing_role, has_data_accesses_managing_role

    def can_user_manage_role_on_perimeter(self, user: User, target_role: Role, target_perimeter: Perimeter, readonly: bool = False) -> bool:
        can_manage_admin_accesses = False
        can_manage_data_accesses = False
        can_manage_jupyter_accesses = False
        can_manage_csv_accesses = False

        if not readonly:
            user_accesses = self.get_user_managing_accesses_on_perimeter(user=user, perimeter=target_perimeter)
        else:
            user_accesses = self.get_user_reading_accesses_on_perimeter(user=user, perimeter=target_perimeter)

        for access in user_accesses:
            role = access.role
            (can_manage_admin_accesses_2,
             can_manage_data_accesses_2) = self.check_accesses_managing_roles_on_perimeter(access=access,
                                                                                           target_perimeter=target_perimeter,
                                                                                           readonly=readonly)
            can_manage_admin_accesses = can_manage_admin_accesses or can_manage_admin_accesses_2
            can_manage_data_accesses = can_manage_data_accesses or can_manage_data_accesses_2
            can_manage_jupyter_accesses = can_manage_jupyter_accesses or role.right_manage_export_jupyter_accesses
            can_manage_csv_accesses = can_manage_csv_accesses or role.right_manage_export_csv_accesses

        return not target_role.requires_full_admin_role_to_be_managed \
            and (can_manage_admin_accesses or not target_role.requires_admin_accesses_managing_role_to_be_managed) \
            and (can_manage_data_accesses or not target_role.requires_data_accesses_managing_role_to_be_managed) \
            and (can_manage_jupyter_accesses or not target_role.requires_jupyter_accesses_managing_role_to_be_managed) \
            and (can_manage_csv_accesses or not target_role.requires_csv_accesses_managing_role_to_be_managed)

    def can_user_manage_access(self, user: User, role: Role, perimeter: Perimeter) -> bool:
        return self.can_user_manage_role_on_perimeter(user, role, perimeter)

    def can_user_read_access(self, user: User, role: Role, perimeter: Perimeter) -> bool:
        return self.can_user_read_role_on_perimeter(user, role, perimeter)


accesses_service = AccessesService()
