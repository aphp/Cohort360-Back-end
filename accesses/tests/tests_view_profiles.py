from __future__ import annotations
import random
from datetime import timedelta
from typing import List
from unittest import mock
from unittest.mock import Mock

from django.utils import timezone
from rest_framework import status
from rest_framework.test import force_authenticate

from accesses.models import Access, Profile, \
    MANUAL_SOURCE, Role
from accesses.views import ProfileViewSet
from admin_cohort.models import User
from admin_cohort.tests_tools import random_str, \
    new_user_and_profile, CaseRetrieveFilter, ViewSetTestsWithBasicPerims, \
    ListCase, CreateCase, DeleteCase, PatchCase, RequestCase
from admin_cohort.tools import prettify_json, prettify_dict
from admin_cohort.types import IdResp

PROFILES_URL = "/profiles"


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


class CheckedProfile:
    def __init__(self, o: dict):
        errs = {}
        for f in ['firstname', 'lastname', 'user_id', 'email']:
            if f not in o or not isinstance(o.get(f), str):
                errs.setdefault(f, f'Missing or wrong type : {o.get(f, "")}')
        if len(errs) > 0:
            raise Exception(prettify_dict(errs))

        self.user: dict = o.get('user', None)
        self.manual_profile: dict = o.get('manual_profile', None)

    def assert_match_id_resp(self, other: CheckedProfile):
        errs: dict = {}
        for s in ['firstname', 'lastname', 'user_id', 'email']:
            if getattr(self, s, "") != getattr(other, s, ""):
                errs.setdefault(
                    s, f"Different: expected is {getattr(self, s)}, "
                       f"got is {getattr(other, s)}")

        if self.user is not None and \
                self.user.get('provider_username') \
                != other.user.get('provider_username'):
            errs['user'] = f"Different: " \
                           f"expected {self.user.get('displayed_name')}, " \
                           f"got {other.user.get('displayed_name')}"

        if self.manual_profile is not None \
                and self.manual_profile.get('id') \
                != other.manual_profile.get('id'):
            errs['manual_profile'] = f"Different: " \
                                     f"expected {str(self.manual_profile)}, " \
                                     f"got {str(other.manual_profile)}"
        if len(errs):
            raise Exception(prettify_dict(errs))

    def __str__(self):
        return prettify_dict({
            **self.__dict__,
            'user': str(self.user), 'manual_profile': str(self.manual_profile)})


class CheckCase(RequestCase):
    def __init__(self, mocked_value: IdResp, mock_called: bool = False,
                 to_find: CheckedProfile = None,
                 checked_id: str = '', **kwargs):
        super(CheckCase, self).__init__(**kwargs)
        self.mocked_value = mocked_value
        self.to_find = to_find
        self.checked_id = checked_id
        self.mock_called = mock_called


class ProfileTests(ViewSetTestsWithBasicPerims):
    unupdatable_fields = ["is_active", "valid_start_datetime",
                          "valid_end_datetime", "id"]
    unsettable_default_fields = dict(source=MANUAL_SOURCE, )
    unsettable_fields = ["id"]
    manual_dupplicated_fields = ['valid_start_datetime', 'valid_end_datetime',
                                 'is_active']

    objects_url = "/profiles/"
    retrieve_view = ProfileViewSet.as_view({'get': 'retrieve'})
    list_view = ProfileViewSet.as_view({'get': 'list'})
    create_view = ProfileViewSet.as_view({'post': 'create'})
    delete_view = ProfileViewSet.as_view({'delete': 'destroy'})
    update_view = ProfileViewSet.as_view({'patch': 'partial_update'})
    model = Profile
    model_objects = Profile.objects
    model_fields = Profile._meta.fields

    def setUp(self):
        super(ProfileTests, self).setUp()

        # ROLES
        self.role_full: Role = Role.objects.create(**dict([
            (f, True) for f in self.all_rights
        ]), name='FULL')

        # user with all the rights
        self.user_full_admin, self.prof_full_admin = new_user_and_profile(
            email='full@admin.us')
        Access.objects.create(role=self.role_full, profile=self.prof_full_admin,
                              perimeter_id=self.aphp.id)


class ProfileCaseRetrieveFilter(CaseRetrieveFilter):
    def __init__(self, user_id: str, source: str, exclude: dict = None):
        self.user_id = user_id
        self.source = source

        super(ProfileCaseRetrieveFilter, self).__init__(exclude=exclude)


class ProfileGetListTests(ProfileTests):
    def setUp(self):
        super(ProfileGetListTests, self).setUp()
        # can_read_users
        self.user_that_can_read_users, self.prof_that_can_read_users = \
            new_user_and_profile(email="can@read.users")
        role_read_users = Role.objects.create(right_read_users=True)
        Access.objects.create(
            perimeter_id=self.hospital3.id,
            profile=self.prof_that_can_read_users,
            role=role_read_users
        )

        # cannot_read_users
        self.user_that_cannot_read_users, self.prof_that_cannot_read_users = \
            new_user_and_profile(email="cannot@read.users")
        role_all_but_read_users = Role.objects.create(
            **dict([(r, True) for r in self.all_rights
                    if r != 'right_read_users'])
        )
        Access.objects.create(
            perimeter_id=self.aphp.id,
            profile=self.prof_that_cannot_read_users,
            role=role_all_but_read_users
        )

        self.name_pattern = "pat"
        self.id_pattern = 34

        nb_providers = 500

        self.provider_firstnames = [
                                       random_str(random.randint(4, 8)) for _ in
                                       range(nb_providers - 110)
                                   ] + [
                                       random_str(random.randint(1, 3))
                                       + self.name_pattern
                                       + random_str(random.randint(0, 3)) for _
                                       in range(110)
                                   ]

        self.provider_lastnames = [
                                      random_str(random.randint(4, 8)) for _ in
                                      range(nb_providers - 110)
                                  ] + [
                                      random_str(random.randint(1, 3))
                                      + self.name_pattern
                                      + random_str(random.randint(0, 3)) for _
                                      in range(110)
                                  ]

        self.users_provider_usernames = list(set(
            [str(random.randint(0, 10000000))
             for _ in range(nb_providers - 110)] + [
                f"{random.randint(0, 100)}{self.id_pattern}"
                f"{random.randint(0, 1000)}" for _ in range(110)
            ]))

        self.list_users: List[User] = User.objects.bulk_create([User(
            provider_username=sv,
            firstname=fn,
            lastname=ln,
            email=f"{fn}.{ln}@aphp.fr",
            provider_id=int(sv)
        ) for (sv, fn, ln) in zip(
            self.users_provider_usernames,
            self.provider_firstnames,
            self.provider_lastnames
        )])

        self.sources = [
            random_str(random.randint(0, 3))
            + self.name_pattern
            + random_str(random.randint(0, 3)) for _ in range(2)
        ]

        self.list_profs: List[Profile] = Profile.objects.bulk_create(sum([[
            Profile(
                provider_id=u.provider_id,
                provider_name=f"{u.firstname} {u.lastname}",
                firstname=u.firstname,
                lastname=u.lastname,
                email=u.email,
                source=s,
                user=u,
                is_active=random.random() < 0.8
            ) for s in random.sample(self.sources, 2)]
            for u in self.list_users], [])) + [
                                             self.prof_that_cannot_read_users,
                                             self.prof_that_can_read_users,
                                             self.prof_full_admin]

    def test_admin_get_all_ph(self):
        # As a user with read_users right, I can get all profiles
        case = ListCase(
            to_find=[*self.list_profs],
            success=True,
            status=status.HTTP_200_OK,
            user=self.user_that_can_read_users
        )
        self.check_get_paged_list_case(case)

    def test_err_admin_get_all_ph(self):
        # As a user with all the rights but not read_users one,
        # I cannot see get profile
        case = ListCase(
            to_find=[],
            success=False,
            status=status.HTTP_403_FORBIDDEN,
            user=self.user_that_cannot_read_users
        )
        self.check_get_paged_list_case(case)

    def test_get_list_with_params(self):
        # As a user with read_users right,
        # I can get profiles given query parameters
        basic_case_dict = dict(success=True, status=status.HTTP_200_OK,
                               user=self.user_that_can_read_users)
        cases = [
            ListCase(
                **basic_case_dict,
                title=f"provider_id={self.id_pattern}",
                to_find=[
                    prof for prof in self.list_profs
                    if str(self.id_pattern) == str(prof.provider_id)],
                params=dict(provider_id=self.id_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"source={self.id_pattern}",
                to_find=[
                    prof for prof in self.list_profs
                    if str(self.id_pattern) == prof.source],
                params=dict(source=self.id_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"cdm_source={self.id_pattern}",
                to_find=[
                    prof for prof in self.list_profs
                    if str(self.id_pattern) == prof.source],
                params=dict(cdm_source=self.id_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"user={self.list_users[0].pk}",
                to_find=list(self.list_users[0].profiles.all()),
                params=dict(user=self.list_users[0].pk)
            ),
            ListCase(
                **basic_case_dict,
                title=f"provider_source_value={self.list_users[0].pk}",
                to_find=list(self.list_users[0].profiles.all()),
                params=dict(provider_source_value=self.list_users[0].pk)
            ),
            ListCase(
                **basic_case_dict,
                title=f"provider_name={self.name_pattern}",
                to_find=[prof for prof in self.list_profs
                         if str(self.name_pattern)
                         in str(prof.provider_name)],
                params=dict(provider_name=self.name_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"lastname={self.name_pattern}",
                to_find=[prof for prof in self.list_profs
                         if str(self.name_pattern) in str(prof.lastname)],
                params=dict(lastname=self.name_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"firstname={self.name_pattern}",
                to_find=[prof for prof in self.list_profs
                         if str(self.name_pattern) in str(prof.firstname)],
                params=dict(firstname=self.name_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"email={self.name_pattern}",
                to_find=[prof for prof in self.list_profs
                         if str(self.name_pattern) in str(prof.email)],
                params=dict(email=self.name_pattern)
            ),
            ListCase(
                **basic_case_dict,
                title=f"provider_history_id={self.list_profs[0].id}",
                to_find=[self.list_profs[0]],
                params=dict(provider_history_id=self.list_profs[0].id)
            ),
            ListCase(
                **basic_case_dict,
                title=f"id={self.list_profs[0].id}",
                to_find=[self.list_profs[0]],
                params=dict(id=self.list_profs[0].id)
            ),
            ListCase(
                **basic_case_dict,
                title=f"is_active={False}",
                to_find=list(filter(lambda p: not p.is_active,
                                    self.list_profs)),
                params=dict(is_active=False)
            ),
        ]
        [self.check_get_paged_list_case(case) for case in cases]


class ProfileCreateTests(ProfileTests):
    def setUp(self):
        super(ProfileCreateTests, self).setUp()
        # USERS
        # empty_user
        self.user_empty: User = User.objects.create(
            provider_username=str(random.randint(0, 10000000)),
            lastname="empty_last",
            firstname="empty_last",
            email="em@pty.user",
        )

        # can_add_users
        self.user_that_can_add_users, self.prof_that_can_add_users = \
            new_user_and_profile(email="can@mng.users")
        role_add_users = Role.objects.create(right_add_users=True)
        Access.objects.create(
            perimeter_id=self.hospital3.id,
            profile=self.prof_that_can_add_users,
            role=role_add_users
        )

        self.creation_data = dict(
            provider_id=self.user_empty.provider_id,
            user=self.user_empty.pk,
            firstname=self.user_empty.firstname,
            lastname=self.user_empty.lastname,
            email=self.user_empty.email
        )
        self.basic_create_case = CreateCase(
            data=self.creation_data,
            retrieve_filter=ProfileCaseRetrieveFilter(
                user_id=self.user_empty.pk, source=MANUAL_SOURCE),
            user=None, status=None, success=None,
        )


class ProfileCheckTests(ProfileCreateTests):
    objects_url = "/profiles/check"
    check_view = ProfileViewSet.as_view({'post': 'check_existing_user'})

    @mock.patch('admin_cohort.conf_auth.check_id_aph')
    def check_check_case(self, case: CheckCase, mock_check: Mock):
        mock_check.return_value = case.mocked_value

        request = self.factory.post(
            self.objects_url, data=dict(user_id=case.checked_id), format='json')
        force_authenticate(request, case.user)

        response = self.__class__.check_view(request)
        response.render()

        self.assertEqual(
            response.status_code, case.status,
            msg=(f"{case.description}"
                 + (f" -> {prettify_json(response.content)}"
                    if response.content else "")),
        )
        if case.success:
            if case.to_find is None:
                self.assertIsNone(response.data)
            else:
                res = CheckedProfile(response.data)
                try:
                    res.assert_match_id_resp(case.to_find)
                except Exception as e:
                    self.fail(f"{case.description} - {e}")
        mock_check.assert_called() if case.mock_called \
            else mock_check.assert_not_called()

    def setUp(self):
        super(ProfileCheckTests, self).setUp()

        # cannot_add_users
        self.user_that_cannot_add_users, self.prof_that_cannot_add_users = \
            new_user_and_profile(email="cannot@mng.users")
        role_all_but_add_users = Role.objects.create(
            **dict([(r, True) for r in self.all_rights
                    if r != 'right_add_users']))
        Access.objects.create(
            perimeter_id=self.aphp.id,
            profile=self.prof_that_cannot_add_users,
            role=role_all_but_add_users
        )
        self.user_random, self.prof_random = \
            new_user_and_profile(email="ran@do.m")

        self.unexisting_user_id = str(random.randint(0, 10000000))

        while self.unexisting_user_id in [
            u.provider_username for u in User.objects.all()
        ]:
            self.unexisting_user_id = str(random.randint(0, 10000000))

        self.base_id_resp: IdResp = IdResp(
            firstname='testFn',
            lastname='testLn',
            user_id=self.user_random.provider_username,
            email='em@ai.l',
        )
        self.base_case = CheckCase(
            success=True,
            mock_called=True,
            mocked_value=self.base_id_resp,
            status=status.HTTP_200_OK,
            user=self.user_that_can_add_users,
        )

    def test_check_profile(self):
        # As a user with right_add_users,
        # I can check the existence of a user on the control API,
        # and it returns User and Manual profile if it exists
        self.check_check_case(self.base_case.clone(
            mocked_value=self.base_id_resp,
            to_find=CheckedProfile(dict(
                firstname=self.base_id_resp.firstname,
                lastname=self.base_id_resp.lastname,
                email=self.base_id_resp.email,
                user_id=self.base_id_resp.user_id,
                user=self.user_random.__dict__,
                manual_profile=self.prof_random.__dict__,
            )),
            checked_id=random_str(1),
        ))

    def test_check_profile_not_existing(self):
        # As a user with right_add_users,
        # I can check the existence of a user on the control API,
        # and it returns None if the API's response is empty
        self.check_check_case(self.base_case.clone(
            mocked_value=None,
            to_find=None,
            status=status.HTTP_204_NO_CONTENT,
            checked_id=random_str(1),
        ))

    def test_check_profile_not_existing_user(self):
        # As a user with right_add_users,
        # I can check the existence of a user on the control API,
        # and it returns with empty user and profile if user is not in database
        self.check_check_case(self.base_case.clone(
            mocked_value=IdResp(**{**self.base_id_resp.__dict__,
                                   'user_id': self.unexisting_user_id}),
            to_find=CheckedProfile(dict(
                firstname=self.base_id_resp.firstname,
                lastname=self.base_id_resp.lastname,
                email=self.base_id_resp.email,
                user_id=self.base_id_resp.user_id,
            )),
            checked_id=random_str(1),
        ))

    def test_check_profile_not_existing_profile(self):
        # As a user with right_add_users,
        # I can check the existence of a user on the control API,
        # and it returns with empty profile if user has no manual profile
        user_random_no_profile: User = User.objects.create(
            provider_username=self.unexisting_user_id,
            email=''
        )
        self.check_check_case(self.base_case.clone(
            mocked_value=IdResp(**{**self.base_id_resp.__dict__,
                                   'user_id': self.unexisting_user_id}),
            to_find=CheckedProfile(dict(
                firstname=self.base_id_resp.firstname,
                lastname=self.base_id_resp.lastname,
                email=self.base_id_resp.email,
                user_id=self.base_id_resp.user_id,
                user=user_random_no_profile.__dict__,
            )),
            checked_id=random_str(1),
        ))

    def test_err_check_profile_missing_param(self):
        # As a user with all the rights, I cannot call it
        # without providing 'user_id' parameter
        self.check_check_case(self.base_case.clone(
            mocked_value=self.base_id_resp,
            mock_called=False,
            checked_id=None,
            status=status.HTTP_400_BAD_REQUEST,
            success=False,
            to_find=None,
        ))

    def test_err_check_profile_unauthorized(self):
        # As a user with everything but right_add_users,
        # I cannot check the existence of a user on the control API
        self.check_check_case(self.base_case.clone(
            mocked_value=self.base_id_resp,
            mock_called=False,
            checked_id=None,
            status=status.HTTP_403_FORBIDDEN,
            user=self.user_that_cannot_add_users,
            success=False,
            to_find=None,
        ))


class ProfileCreateWithUserTests(ProfileCreateTests):
    def setUp(self):
        super(ProfileCreateWithUserTests, self).setUp()

        # cannot_add_users
        self.user_that_cannot_add_users, self.prof_that_cannot_add_users = \
            new_user_and_profile(email="cannot@mng.users")
        role_all_but_add_users = Role.objects.create(
            **dict([(r, True) for r in self.all_rights
                    if r != 'right_add_users']))
        Access.objects.create(
            perimeter_id=self.aphp.id,
            profile=self.prof_that_cannot_add_users,
            role=role_all_but_add_users
        )

    def test_create_as_user_admin(self):
        # As a user with right_add_users, I can create a new profile for a user
        # that has no manual profile yet
        case = self.basic_create_case.clone(
            user=self.user_that_can_add_users,
            success=True,
            status=status.HTTP_201_CREATED,
        )
        self.check_create_case(case)

    def test_error_create_as_simple_user(self):
        # As a user with everything but right_add_users,
        # I cannot create a new profile
        case = self.basic_create_case.clone(
            user=self.user_that_cannot_add_users,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_create_case(case)

    def test_error_create_when_existing_profile(self):
        # As a user with right_add_users, I cannot create a new profile to a
        # user that already has a manual profile
        existing_profile: Profile = Profile.objects.create(
            source=MANUAL_SOURCE, user=self.user_empty, manual_is_active=True,
        )

        case = self.basic_create_case.clone(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            retrieve_filter=ProfileCaseRetrieveFilter(
                user_id=self.user_empty.pk, source=MANUAL_SOURCE,
                exclude=dict(id=existing_profile.id)
            ),
        )
        self.check_create_case(case)

    def test_error_create_with_forbidden_fields(self):
        # As a user with right_add_users, when creating a new manual profile
        # specifying a source will return 400.
        cases = [self.basic_create_case.clone(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            data={
                **self.creation_data,
                k: v,
            }
        ) for (k, v) in dict(source="not_manual").items()]
        [self.check_create_case(case) for case in cases]

    def test_create_manual_fields_replacing_fields(self):
        # As a user with right_add_users, when creating a new manual profile
        # the fields valid_start_datetime, valid_end_datetime and is_active will
        # actually fill manual_valid_start_datetime, etc.
        case = self.basic_create_case.clone(
            user=self.user_that_can_add_users,
            success=True,
            status=status.HTTP_201_CREATED,
            data={
                **self.creation_data,
                'valid_start_datetime': timezone.now() - timedelta(days=10),
                'valid_end_datetime': timezone.now() + timedelta(days=10),
                'is_active': False,
            })
        self.check_create_case(case)

    def test_error_create_with_both_field_and_manual_version(self):
        # As a user with right_add_users, when creating a new manual profile
        # specifying a value to one of the previous fields AND to its manual_
        # version will return 400.

        cases = [self.basic_create_case.clone(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            data={
                **self.creation_data,
                k: v,
                f"manual_{k}": v,
            }
        ) for (k, v) in dict(
            valid_start_datetime=(timezone.now() - timedelta(days=10),
                                  timezone.now() - timedelta(days=10)),
            valid_end_datetime=(timezone.now() + timedelta(days=10),
                                timezone.now() + timedelta(days=10)),
            is_active=(False, True),
        ).items()]
        [self.check_create_case(case) for case in cases]


class ProfileCreateWithoutUserTests(ProfileCreateTests):
    def setUp(self):
        super(ProfileCreateWithoutUserTests, self).setUp()

        self.test_prov_id = random.randint(0, 100000)
        self.test_username = str(random.randint(0, 10000000))
        self.test_email = "new@empty.user"

    def check_create_case_without_user(self, case: CreateCase):
        self.check_create_case(case.clone(
            retrieve_filter=ProfileCaseRetrieveFilter(
                user_id=self.test_username, source=MANUAL_SOURCE),
            data=dict(
                user_id=self.test_username,
                firstname=self.user_empty.firstname,
                lastname=self.user_empty.lastname,
                email=self.test_email
            ),
        ))

        inst = User.objects.filter(
            firstname=self.user_empty.firstname,
            lastname=self.user_empty.lastname,
            email=self.test_email,
            provider_username=self.test_username,
            provider_id=self.test_prov_id,
        ).first()

        if case.success:
            self.assertIsNotNone(inst)
        else:
            self.assertIsNone(inst)

    @mock.patch('accesses.serializers.check_id_aph')
    @mock.patch('accesses.serializers.get_provider_id')
    def test_create_as_user_admin_without_user(
            self, mock_get_prov: Mock, mock_check_id_aph: Mock):
        # As a user with right_add_users, I can create a profile for a
        # non existing user, this will also create a User
        mock_check_id_aph.return_value = dict()
        mock_get_prov.return_value = self.test_prov_id

        case = self.basic_create_case.clone(
            user=self.user_that_can_add_users,
            success=True,
            status=status.HTTP_201_CREATED,
        )
        self.check_create_case_without_user(case)

        mock_check_id_aph.assert_called_once()
        mock_get_prov.assert_called_once()

    @mock.patch('accesses.serializers.check_id_aph')
    @mock.patch('accesses.serializers.get_provider_id')
    def test_err_create_with_forbidden_id(
            self, mock_get_prov: Mock, mock_check_id_aph: Mock):
        # As a user with right_add_users, I cannot create a profile for a
        # non existing user if id is not validated with check_id_aph
        mock_check_id_aph.side_effect = Exception()
        mock_get_prov.return_value = self.test_prov_id

        case = self.basic_create_case.clone(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.check_create_case_without_user(case)
        mock_check_id_aph.assert_called_once()
        mock_get_prov.assert_not_called()

    @mock.patch('accesses.serializers.check_id_aph')
    @mock.patch('accesses.serializers.get_provider_id')
    def test_err_create_provider_id_not_found(
            self, mock_get_prov: Mock, mock_check_id_aph: Mock):
        # As a user with right_add_users, I cannot create a profile for a
        # non existing user if provider_id is not found by get_provider_id
        mock_check_id_aph.return_value = dict()
        mock_get_prov.side_effect = Exception()

        case = self.basic_create_case.clone(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
        )
        self.check_create_case_without_user(case)
        mock_check_id_aph.assert_called_once()
        mock_get_prov.assert_called_once()


class ProfilePatchTests(ProfileTests):
    def setUp(self):
        super(ProfilePatchTests, self).setUp()
        # USERS
        # empty_user
        self.user_empty: User = User.objects.create(
            provider_username=str(random.randint(0, 10000000)),
            lastname="empty_last",
            firstname="empty_last",
            email="em@pty.user",
        )

        # can_edit_users
        self.user_that_can_edit_users, self.prof_that_can_edit_users = \
            new_user_and_profile(email="can@mng.users")
        role_edit_users = Role.objects.create(right_edit_users=True)
        Access.objects.create(
            perimeter_id=self.hospital3.id,
            profile=self.prof_that_can_edit_users,
            role=role_edit_users
        )

        # cannot_edit_users
        self.user_that_cannot_edit_users, self.prof_that_cannot_edit_users = \
            new_user_and_profile(email="cannot@mng.users")
        role_all_but_edit_users = Role.objects.create(
            **dict([(r, True) for r in self.all_rights
                    if r != 'right_edit_users']))
        Access.objects.create(
            perimeter_id=self.aphp.id,
            profile=self.prof_that_cannot_edit_users,
            role=role_all_but_edit_users
        )

        self.created_data = dict(
            provider_id=self.user_empty.provider_id,
            user=self.user_empty,
            firstname=self.user_empty.firstname,
            lastname=self.user_empty.lastname,
            email=self.user_empty.email,
            is_active=True,
        )
        self.base_data_to_update = dict(
            provider_name='new',
            firstname='new',
            lastname='new',
            email='new',
            provider_id=random.randint(0, 1000000),
            is_active=False,
            valid_start_datetime=timezone.now() - timedelta(days=2),
            valid_end_datetime=timezone.now() + timedelta(days=2),
        )
        self.basic_patch_case = PatchCase(
            initial_data=self.created_data,
            data_to_update=self.base_data_to_update,
            user=None, status=None, success=None,
        )

    def test_patch_as_user_admin(self):
        # As a user with right_edit_users, I can edit a profile
        case = self.basic_patch_case.clone(
            user=self.user_that_can_edit_users,
            success=True,
            status=status.HTTP_200_OK,
        )
        self.check_patch_case(case)

    def test_error_patch_as_simple_user(self):
        # As a user with everything but right_edit_users,
        # I cannot edit a profile
        case = self.basic_patch_case.clone(
            user=self.user_that_cannot_edit_users,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
        )
        self.check_patch_case(case)

    def test_error_patch_with_forbidden_fields(self):
        # As a user with all the rights,
        # I cannot edit a profile with certain fields
        other_user_empty = User.objects.create(email="other_em@pty.user")
        cases = [self.basic_patch_case.clone(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_400_BAD_REQUEST,
            data_to_update={k: v}
        ) for (k, v) in dict(user=other_user_empty.pk, source='other').items()]
        [self.check_patch_case(case) for case in cases]


class ProfileDeleteTests(ProfileTests):
    def setUp(self):
        super(ProfileDeleteTests, self).setUp()
        # empty_user
        self.user_empty: User = User.objects.create(
            provider_username=str(random.randint(0, 10000000)),
            lastname="empty_last",
            firstname="empty_last",
            email="em@pty.user",
        )

    def test_error_delete_user_as_main_admin(self):
        # As a user will all the rights,
        # I cannot delete a profile
        cases = [DeleteCase(
            user=self.user_full_admin,
            success=False,
            status=status.HTTP_403_FORBIDDEN,
            data_to_delete=dict(user=self.user_empty, source=s)
        ) for s in [MANUAL_SOURCE, 'RandomSource']]
        [self.check_delete_case(case) for case in cases]
