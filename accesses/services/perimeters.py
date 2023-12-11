from typing import Set, List

from django.db.models import QuerySet, Q

from accesses.models import Perimeter, Role
from accesses.services.accesses import accesses_service
from accesses.services.shared import PerimeterReadRight
from admin_cohort.models import User
from admin_cohort.settings import PERIMETERS_TYPES
from admin_cohort.tools import join_qs
from cohort.tools import get_list_cohort_id_care_site


class PerimetersService:

    @staticmethod
    def get_all_child_perimeters(perimeter: Perimeter) -> QuerySet:
        return Perimeter.objects.filter(join_qs([Q(**{"__".join(i * ["parent"]): perimeter})
                                                 for i in range(1, len(PERIMETERS_TYPES))]))

    @staticmethod
    def get_top_perimeters_ids_same_level(same_level_perimeters_ids: List[int], all_perimeters_ids: List[int]) -> Set[int]:
        """
        * If any of the parent perimeters of P is already linked to an access (same level OR inferior levels),
          then, perimeter P is not the highest perimeter in its relative hierarchy (branch), i.e. one of its parents is.
        * We assume that a right of type "manage same level" allows to manage accesses on "same level" and "inferior levels".
          Given the hierarchy in the docstring bellow:
             For example, having access on P2 allows to manage accesses on inferior levels as well, in particular on P8.
             The given access on P8 is then considered redundant.
        regarding the hierarchy below, the top perimeters with accesses of type "manage same level" are: P1 and P2
        """
        top_perimeters_ids = set()
        for p in Perimeter.objects.filter(id__in=same_level_perimeters_ids):
            if any(parent_id in all_perimeters_ids for parent_id in p.above_levels):
                continue
            top_perimeters_ids.add(p.id)
        return top_perimeters_ids

    @staticmethod
    def get_top_perimeter_ids_inf_levels(inf_levels_perimeters_ids: List[int],
                                         all_perimeters_ids: List[int],
                                         top_same_level_perimeters_ids: Set[int]) -> Set[int]:
        """
        Get the highest perimeters on which are defined accesses allowing to manage other accesses on inf levels ONLY.
        --> The manageable perimeters will be their direct children (because accesses here allow to manage on inf levels ONLY).
        Regarding the hierarchy below, the top perimeters with accesses of type "manage inf levels" are the children of P0: P3, P4 and P5
        """
        top_perimeters_ids = []
        for p in Perimeter.objects.filter(id__in=inf_levels_perimeters_ids):
            if p.id not in top_same_level_perimeters_ids and all(parent_id not in all_perimeters_ids for parent_id in p.above_levels):
                children_ids = p.inferior_levels
                if not children_ids:
                    continue
                top_perimeters_ids.extend(children_ids)
        return set(top_perimeters_ids)

    def get_top_manageable_perimeters(self, user: User) -> QuerySet:
        """
        The user has 6 accesses allowing him to manage other accesses either on same level or on inferior levels.
        Accesses are defined on perimeters: P0, P1, P2, P5, P8 and P10
                                               APHP
                     ___________________________|____________________________
                    |                           |                           |
                    P0 (Inf)                    P1 (Same + Inf)             P2 (Same)
           _________|__________           ______|_______           _________|__________
          |         |         |          |             |          |         |         |
          P3        P4       P5 (Same)   P6            P7       P8 (Same)   P9       P10 (Inf)
              ______|_______                                                    ______|_______
             |             |                                                   |             |
            P11           P12                                                 P13           P14
        """
        user_accesses = accesses_service.get_user_valid_accesses(user=user)
        if accesses_service.user_is_full_admin(user=user) or all(access.role.has_any_global_management_right()
                                                                 and not access.role.has_any_level_dependent_management_right()
                                                                 for access in user_accesses):
            return Perimeter.objects.filter(parent__isnull=True)
        else:
            same_level_accesses = user_accesses.filter(Role.q_allow_manage_accesses_on_same_level())
            inf_levels_accesses = user_accesses.filter(Role.q_allow_manage_accesses_on_inf_levels())

            same_level_perimeters_ids = [access.perimeter.id for access in same_level_accesses]
            inf_levels_perimeters_ids = [access.perimeter.id for access in inf_levels_accesses]
            all_perimeters_ids = same_level_perimeters_ids + inf_levels_perimeters_ids

            top_same_level_perimeters_ids = self.get_top_perimeters_ids_same_level(same_level_perimeters_ids=same_level_perimeters_ids,
                                                                                   all_perimeters_ids=all_perimeters_ids)
            top_inf_levels_perimeters_ids = self.get_top_perimeter_ids_inf_levels(inf_levels_perimeters_ids=inf_levels_perimeters_ids,
                                                                                  all_perimeters_ids=all_perimeters_ids,
                                                                                  top_same_level_perimeters_ids=top_same_level_perimeters_ids)
            return Perimeter.objects.filter(id__in=top_same_level_perimeters_ids.union(top_inf_levels_perimeters_ids))

    @staticmethod
    def get_target_perimeters(cohort_ids: str, owner: User) -> QuerySet:
        virtual_cohort_ids = get_list_cohort_id_care_site(cohorts_ids=[int(cohort_id) for cohort_id in cohort_ids.split(",")],
                                                          all_user_cohorts=owner.user_cohorts.all())
        return Perimeter.objects.filter(cohort_id__in=virtual_cohort_ids)

    @staticmethod
    def get_top_perimeters_with_right_read_nomi(read_nomi_perimeters_ids: List[int]) -> List[int]:
        """ for each perimeter with nominative read right, remove it if any of its parents has nomi access """
        for perimeter in Perimeter.objects.filter(id__in=read_nomi_perimeters_ids):
            if any(parent_id in read_nomi_perimeters_ids for parent_id in perimeter.above_levels):
                try:
                    read_nomi_perimeters_ids.remove(perimeter.id)
                except ValueError:
                    continue
        return read_nomi_perimeters_ids

    @staticmethod
    def get_top_perimeters_with_right_read_pseudo(top_read_nomi_perimeters_ids: List[int],
                                                  read_pseudo_perimeters_ids: List[int]) -> List[int]:
        """ for each perimeter with pseudo read right, remove it if it has nomi access too
            or if any of its parents has nomi or pseudo access
        """
        for perimeter in Perimeter.objects.filter(id__in=read_pseudo_perimeters_ids):
            if any((parent_id in read_pseudo_perimeters_ids
                    or parent_id in top_read_nomi_perimeters_ids
                    or perimeter.id in top_read_nomi_perimeters_ids) for parent_id in perimeter.above_levels):
                try:
                    read_pseudo_perimeters_ids.remove(perimeter.id)
                except ValueError:
                    continue
        return read_pseudo_perimeters_ids

    @staticmethod
    def get_perimeters_read_rights(target_perimeters: QuerySet,
                                   top_read_nomi_perimeters_ids: List[int],
                                   top_read_pseudo_perimeters_ids: List[int],
                                   allow_search_by_ipp: bool,
                                   allow_read_opposed_patient: bool) -> List[PerimeterReadRight]:
        perimeter_read_right_list = []

        if not (top_read_nomi_perimeters_ids or top_read_pseudo_perimeters_ids):
            return perimeter_read_right_list

        for perimeter in target_perimeters:
            perimeter_and_parents_ids = [perimeter.id] + perimeter.above_levels
            read_nomi, read_pseudo = False, False
            if any(perimeter_id in top_read_nomi_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
                read_nomi, read_pseudo = True, True
            elif any(perimeter_id in top_read_pseudo_perimeters_ids for perimeter_id in perimeter_and_parents_ids):
                read_pseudo = True
            perimeter_read_right_list.append(PerimeterReadRight(perimeter=perimeter,
                                                                right_read_patient_nominative=read_nomi,
                                                                right_read_patient_pseudonymized=read_pseudo,
                                                                right_search_patients_by_ipp=allow_search_by_ipp,
                                                                right_read_opposed_patients_data=allow_read_opposed_patient))
        return perimeter_read_right_list

    def get_data_reading_rights_on_perimeters(self, user: User, target_perimeters: QuerySet) -> List[PerimeterReadRight]:
        user_accesses = accesses_service.get_user_valid_accesses(user=user)
        read_patient_nominative_accesses = user_accesses.filter(Role.q_allow_read_patient_data_nominative())
        read_patient_pseudo_accesses = user_accesses.filter(Role.q_allow_read_patient_data_pseudo() |
                                                            Role.q_allow_read_patient_data_nominative())
        allow_search_by_ipp = user_accesses.filter(Role.q_allow_search_patients_by_ipp()).exists()
        allow_read_opposed_patient = user_accesses.filter(Role.q_allow_read_research_opposed_patient_data()).exists()

        read_nomi_perimeters_ids = [access.perimeter_id for access in read_patient_nominative_accesses]
        read_pseudo_perimeters_ids = [access.perimeter_id for access in read_patient_pseudo_accesses]

        top_read_nomi_perimeters_ids = self.get_top_perimeters_with_right_read_nomi(read_nomi_perimeters_ids=read_nomi_perimeters_ids)
        top_read_pseudo_perimeters_ids = self.get_top_perimeters_with_right_read_pseudo(top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                                                        read_pseudo_perimeters_ids=read_pseudo_perimeters_ids)

        perimeters_read_rights = self.get_perimeters_read_rights(target_perimeters=target_perimeters,
                                                                 top_read_nomi_perimeters_ids=top_read_nomi_perimeters_ids,
                                                                 top_read_pseudo_perimeters_ids=top_read_pseudo_perimeters_ids,
                                                                 allow_search_by_ipp=allow_search_by_ipp,
                                                                 allow_read_opposed_patient=allow_read_opposed_patient)
        return perimeters_read_rights


perimeters_service = PerimetersService()
