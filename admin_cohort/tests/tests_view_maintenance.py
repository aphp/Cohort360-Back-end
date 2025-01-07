import datetime
import random
from datetime import timedelta
from typing import List, Tuple

from django.utils import timezone
from rest_framework import status

from accesses.models import Access, Role
from admin_cohort.models import MaintenancePhase
from admin_cohort.tests.tests_tools import new_user_and_profile, \
    CaseRetrieveFilter, ViewSetTestsWithBasicPerims, ListCase, \
    CreateCase, DeleteCase, PatchCase, RetrieveCase
from admin_cohort.views import MaintenancePhaseViewSet


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


class MaintenanceTests(ViewSetTestsWithBasicPerims):
    unupdatable_fields = []
    unsettable_default_fields = dict()
    unsettable_fields = []
    manual_dupplicated_fields = []

    objects_url = "/maintenances/"
    retrieve_view = MaintenancePhaseViewSet.as_view({'get': 'retrieve'})
    list_view = MaintenancePhaseViewSet.as_view({'get': 'list'})
    create_view = MaintenancePhaseViewSet.as_view({'post': 'create'})
    delete_view = MaintenancePhaseViewSet.as_view({'delete': 'destroy'})
    update_view = MaintenancePhaseViewSet.as_view({'patch': 'partial_update'})
    model = MaintenancePhase
    model_objects = MaintenancePhase.objects
    model_fields = MaintenancePhase._meta.fields

    def setUp(self):
        super(MaintenanceTests, self).setUp()

        self.user_maintenance_manager, profile_maintenance_manager = new_user_and_profile()
        self.role_maintenance_manager = Role.objects.create(right_full_admin=True)
        Access.objects.create(perimeter_id=self.hospital3.id,
                              profile=profile_maintenance_manager,
                              role=self.role_maintenance_manager,
                              start_datetime=timezone.now(),
                              end_datetime=timezone.now() + timedelta(days=365))

        self.user_not_maintenance_manager, profile_not_maintenance_manager = new_user_and_profile()
        self.role_all_but_edit_maintenances = Role.objects.create(**dict([(r, True) for r in self.all_rights
                                                                          if r != 'right_full_admin']))
        Access.objects.create(perimeter_id=self.aphp.id,
                              profile=profile_not_maintenance_manager,
                              role=self.role_all_but_edit_maintenances,
                              start_datetime=timezone.now(),
                              end_datetime=timezone.now() + timedelta(days=365))


class MaintenanceCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, subject: str, exclude: dict = None):
        self.subject = subject
        super(MaintenanceCaseRetrieveFilter, self).__init__(exclude=exclude)


class MaintenanceGetTests(MaintenanceTests):
    def setUp(self):
        super(MaintenanceGetTests, self).setUp()
        # can_read_mtnces
        self.user_with_no_right, self.prof_with_no_right = \
            new_user_and_profile()


class MaintenanceGetListTests(MaintenanceGetTests):
    def setUp(self):
        super(MaintenanceGetListTests, self).setUp()
        self.name_pattern = "pat"

        mtnces_names = [f"{self.name_pattern}_{i}" if i % 2 else f"maint_{i}" for i in range(20)]

        self.ref_now: datetime.datetime = timezone.now()

        self.list_mtnces: List[MaintenancePhase] = \
            MaintenancePhase.objects.bulk_create([MaintenancePhase(
                subject=name,
                start_datetime=(self.ref_now
                                + timedelta(days=random.randint(-10, 10))),
                end_datetime=(self.ref_now
                              + timedelta(days=random.randint(-10, 10))),
            ) for name in mtnces_names])

    def test_get_all_mtnces(self):
        # As a user with no right, I can get all maintenance phases
        case = ListCase(
            to_find=[*self.list_mtnces],
            success=True,
            status=status.HTTP_200_OK,
            user=self.user_with_no_right
        )
        self.check_get_paged_list_case(case)

    def test_get_list_with_params(self):
        # As a user with no right,
        # I can get maintenance phases filtered given query parameters:
        basic_case_dict = dict(success=True, status=status.HTTP_200_OK,
                               user=self.user_with_no_right)
        cases = [
            ListCase(
                # - start_datetime
                **basic_case_dict,
                title=f"start_datetime={self.ref_now}",
                to_find=[mtnce for mtnce in self.list_mtnces
                         if self.ref_now == mtnce.start_datetime],
                params=dict(start_datetime=self.ref_now)
            ),
            ListCase(
                # - end_datetime
                **basic_case_dict,
                title=f"end_datetime={self.ref_now}",
                to_find=[mtnce for mtnce in self.list_mtnces
                         if self.ref_now == mtnce.end_datetime],
                params=dict(end_datetime=self.ref_now)
            ),
            ListCase(
                # - search (on 'subject')
                **basic_case_dict,
                title=f"search={self.name_pattern}",
                to_find=[mtnce for mtnce in self.list_mtnces
                         if str(self.name_pattern) in str(mtnce.subject)],
                params=dict(search=self.name_pattern)
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]


class MaintenanceGetNextTests(MaintenanceGetTests):
    # As a user with no right,
    # I can get the next maintenance phase, given the rules:
    objects_url = "/maintenances/next"
    retrieve_view = MaintenancePhaseViewSet.as_view({'get': 'next'})

    def setUp(self):
        super(MaintenanceGetNextTests, self).setUp()
        self.base_case = RetrieveCase(
            user=self.user_with_no_right,
            status=status.HTTP_200_OK,
            success=True,
        )

    @staticmethod
    def prepare_maintenances(
            nb_days: List[Tuple[int, int]]) -> List[MaintenancePhase]:
        return MaintenancePhase.objects.bulk_create([MaintenancePhase(
            start_datetime=timezone.now() + timedelta(days=m),
            end_datetime=timezone.now() + timedelta(days=n)
        ) for (m, n) in nb_days])

    def test_get_earlier_next_1(self):
        # if there are no phase with start_datetime < now < end_datetime,
        # and if there are one or more phases with now < start_datetime,
        # return the one with lowest end_datetime
        # t (A ( ) B)
        # 0    2    4  ->
        m_a, m_b = self.prepare_maintenances([(1, 3), (2, 4)])
        self.check_retrieve_case(self.base_case.clone(
            title="t (A ( ) B)",
            to_find=m_a,
        ))

    def test_get_earlier_next_2(self):
        # if there are no phase with start_datetime < now < end_datetime,
        # and if there are one or more phases with now < start_datetime,
        # return the one with lowest end_datetime
        # t (A ( B ) A)
        # 0    2      4  ->
        m_a, m_b = self.prepare_maintenances([(1, 4), (2, 3)])
        self.check_retrieve_case(self.base_case.clone(
            title="t (A ( B ) A)",
            to_find=m_a,
        ))

    def test_get_later_current_1(self):
        # if there are one or more phases
        # with start_datetime < now < end_datetime
        # return the one with highest end_datetime
        #  (A ( t )  B)
        # -2    0     2  ->
        m_a, m_b = self.prepare_maintenances([(-2, 1), (-1, 2)])
        self.check_retrieve_case(self.base_case.clone(
            title="(B ( t )  C)",
            to_find=m_b,
        ))

    def test_get_later_current_2(self):
        # if there are one or more phases
        # with start_datetime < now < end_datetime
        # return the one with highest end_datetime
        # (A ( Bt ) A)
        m_a, m_b = self.prepare_maintenances([(-2, 2), (-1, 1)])
        self.check_retrieve_case(self.base_case.clone(
            title="(A ( Bt ) A)",
            to_find=m_a,
        ))

    def test_get_next_none_coming(self):
        # if no phase with start_datetime > now or end_datetime > now, return {}
        # ( A )( B ) t
        #    -3   -1 0  ->
        self.prepare_maintenances([(-4, -3), (-2, -1)])
        self.check_retrieve_case(self.base_case.clone(
            title="( A )( B ) t",
            to_find=None,
        ))


class MaintenanceCreateTests(MaintenanceTests):
    def setUp(self):
        super(MaintenanceCreateTests, self).setUp()

        test_subject = 'test_subject'
        self.creation_data = dict(
            subject=test_subject,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
        )
        self.basic_create_case = CreateCase(
            data=self.creation_data,
            retrieve_filter=MaintenanceCaseRetrieveFilter(subject=test_subject),
            user=None, status=None, success=None,
        )

    def test_create_as_admin(self):
        # As a user with right_full_admin, I can create a maintenance phase
        case = self.basic_create_case.clone(
            user=self.user_maintenance_manager,
            success=True,
            status=status.HTTP_201_CREATED,
        )
        self.check_create_case(case)

    def test_error_create_as_simple_user(self):
        # As a user with everything but right_full_admin,
        # I cannot create a maintenance phase
        case = self.basic_create_case.clone(
            user=self.user_not_maintenance_manager,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_create_case(case)

    def test_error_create_wrong_mtnc(self):
        # As a user with all the rights, I cannot create a maintenance phase
        # if start_datetime > end_datetime
        cases = [self.basic_create_case.clone(
            user=self.user_maintenance_manager,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            data=d,
            title=t,
        ) for (d, t) in [
            ({**self.creation_data,
              'start_datetime': (self.creation_data.get('end_datetime')
                                 + timedelta(seconds=1))
              }, "start > end"),
            # ({**self.creation_data,
            #   'start_datetime': (timezone.now() - timedelta(days=2)),
            #   'end_datetime': (timezone.now() - timedelta(days=1))
            #   }, "in the past")
        ]]
        [self.check_create_case(case) for case in cases]


class MaintenancePatchTests(MaintenanceTests):
    def setUp(self):
        super(MaintenancePatchTests, self).setUp()

        self.created_data = dict(
            subject='created',
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=3),
        )
        self.base_data_to_update = dict(
            subject='updated',
            start_datetime=timezone.now() + timedelta(days=2),
            end_datetime=timezone.now() + timedelta(days=4),
        )
        self.basic_patch_case = PatchCase(
            initial_data=self.created_data,
            data_to_update=self.base_data_to_update,
            user=None, status=None, success=None,
        )

    def test_patch_as_user_admin(self):
        # As a user with right_full_admin, I can edit a maintenance phase
        cases = [self.basic_patch_case.clone(
            user=self.user_maintenance_manager,
            success=True,
            status=status.HTTP_200_OK,
            data_to_update=dict({k: v})
        ) for (k, v) in self.base_data_to_update.items()]
        [self.check_patch_case(case) for case in cases]

    def test_error_patch_as_simple_user(self):
        # As a user with everything but right_full_admin,
        # I cannot edit a maintenance phase
        case = self.basic_patch_case.clone(
            user=self.user_not_maintenance_manager,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_patch_case(case)

    def test_error_wrong_data(self):
        # As a user with all the rights,
        # I cannot edit a maintenance phase with start_datetime > end_datetime
        cases = [self.basic_patch_case.clone(
            user=self.user_maintenance_manager,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            data_to_update=d,
            title=t,
        ) for (d, t) in [
            ({**self.base_data_to_update,
              'start_datetime': (self.base_data_to_update.get('end_datetime')
                                 + timedelta(seconds=1))
              }, "start > end"),
            ({'start_datetime': (self.created_data.get('end_datetime')
                                 + timedelta(seconds=1))
              }, "start > end but patching start only"),
            ({'end_datetime': (self.created_data.get('start_datetime')
                               - timedelta(seconds=1))
              }, "start > end but patching end only"),

            # ({**self.base_data_to_update,
            #   'start_datetime': (timezone.now() - timedelta(days=2)),
            #   'end_datetime': (timezone.now() - timedelta(days=1))
            #   }, "in the past")
        ]]
        [self.check_patch_case(case) for case in cases]


class MaintenanceDeleteTests(MaintenanceTests):
    def setUp(self):
        super(MaintenanceDeleteTests, self).setUp()

        self.created_data = dict(
            subject='created',
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=2),
        )
        self.basic_delete_case = DeleteCase(
            data_to_delete=self.created_data,
            user=None, status=None, success=None,
        )

    def test_delete_user_as_main_admin(self):
        # As a user with right_full_admin, I can delete a maintenance phase
        case = self.basic_delete_case.clone(
            user=self.user_maintenance_manager,
            success=True,
            status=status.HTTP_204_NO_CONTENT,
        )
        self.check_delete_case(case)

    def test_error_delete_user_as_simple_user(self):
        # As a user with everything but right_full_admin,
        # I cannot delete a maintenance phase
        case = self.basic_delete_case.clone(
            user=self.user_not_maintenance_manager,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_delete_case(case)
