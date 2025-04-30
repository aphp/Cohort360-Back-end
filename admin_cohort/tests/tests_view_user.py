from datetime import timedelta
from unittest import mock

from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.test import force_authenticate

from accesses.models import Access, Role, Perimeter, Profile
from admin_cohort.exceptions import ServerError
from admin_cohort.models import User
from admin_cohort.tests.tests_tools import BaseTests
from admin_cohort.views import UserViewSet

USERS_URL = "/users"

MANUAL_SOURCE = settings.ACCESS_SOURCES[0]


class ObjectView(object):
    def __init__(self, d):
        self.__dict__ = d


class UserTests(BaseTests):
    def setUp(self):
        super(UserTests, self).setUp()
        #         main_admin(aphp)
        #        /    \
        # u1admin(h1)  u2admin(h2)
        #                |
        #             u1pseudo(h3)
        self.aphp = Perimeter.objects.create(**dict(local_id=1,
                                                    name="APHP",
                                                    parent=None,
                                                    type_source_value=settings.PERIMETER_TYPES[0],
                                                    source_value="APHP"))
        self.hospital1 = Perimeter.objects.create(**dict(local_id=11,
                                                         name="Hospital 01",
                                                         parent=self.aphp,
                                                         type_source_value=settings.PERIMETER_TYPES[2],
                                                         source_value="Hospital 01"))
        self.hospital2 = Perimeter.objects.create(**dict(local_id=12,
                                                         name="Hospital 02",
                                                         parent=self.aphp,
                                                         type_source_value=settings.PERIMETER_TYPES[2],
                                                         source_value="Hospital 02"))
        self.hospital3 = Perimeter.objects.create(**dict(local_id=13,
                                                         name="Hospital 03",
                                                         parent=self.aphp,
                                                         type_source_value=settings.PERIMETER_TYPES[2],
                                                         source_value="Hospital 03"))

        self.role_full_admin = Role.objects.create(**dict([(f, True) for f in self.all_rights]), name='Admin full role')
        self.pseudo_anonymised_data_role = Role.objects.create(**{**dict([(f, False) for f in self.all_rights]),
                                                                  "right_read_patient_pseudonymized": True},
                                                               name='Pseudo anonymised data role')

        self.admin_user = User.objects.create(username="000000", firstname="Admin", lastname="ADMIN", email="admin@aphp.fr")
        self.user1 = User.objects.create(username="1111111", firstname="User 01", lastname="USER01", email="user01@aphp.fr")
        self.user2 = User.objects.create(username="2222222", firstname="User 02", lastname="USER02", email="user02@aphp.fr")
        self.user3 = User.objects.create(username="3333333", firstname="User 03", lastname="USER03", email="user03@aphp.fr")

        self.admin_profile = Profile.objects.create(source=MANUAL_SOURCE, user=self.admin_user, is_active=True)
        self.profile1 = Profile.objects.create(source=MANUAL_SOURCE, user=self.user1, is_active=True)
        self.profile2 = Profile.objects.create(source=MANUAL_SOURCE, user=self.user2, is_active=True)
        self.profile3 = Profile.objects.create(source=MANUAL_SOURCE, user=self.user3, is_active=False)

        self.admin_access = Access.objects.create(perimeter_id=self.aphp.id,
                                                  role=self.role_full_admin,
                                                  profile=self.admin_profile,
                                                  start_datetime=timezone.now(),
                                                  end_datetime=timezone.now() + timedelta(days=365))
        self.access_user1_admin_h1 = Access.objects.create(perimeter_id=self.hospital1.id,
                                                           role=self.role_full_admin,
                                                           profile=self.profile1,
                                                           start_datetime=timezone.now(),
                                                           end_datetime=timezone.now() + timedelta(days=365))
        self.access_user2_admin_h2 = Access.objects.create(perimeter_id=self.hospital2.id,
                                                           role=self.role_full_admin,
                                                           profile=self. profile2,
                                                           start_datetime=timezone.now(),
                                                           end_datetime=timezone.now() + timedelta(days=365))
        self.access_user1_pseudo_h3 = Access.objects.create(perimeter_id=self.hospital3.id,
                                                            role=self.pseudo_anonymised_data_role,
                                                            profile=self. profile1,
                                                            start_datetime=timezone.now(),
                                                            end_datetime=timezone.now() + timedelta(days=365))


class UserTestsAsAdmin(UserTests):

    def test_get_user_as_main_admin(self):
        # As a main admin, I can get a user's full data
        request = self.factory.get(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'retrieve'})(request, username=self.user1.username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        user_found = ObjectView(self.get_response_payload(response))
        self.assertEqual(user_found.username, self.user1.username)
        self.assertEqual(user_found.email, self.user1.email)

    def _get_users(self, filter_active: bool):
        request = self.factory.get(USERS_URL+("?with_access=true" if filter_active else ""))
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'list'})(request)
        response.render()
        return response

    def _check_users(self, response, users_to_find):
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        users_found = [ObjectView(u) for u in self.get_response_payload(response)["results"]]

        user_found_ids = [p.username for p in users_found]
        users_to_find_ids = [p.username for p in users_to_find]
        msg = "\n".join(["", "got", str(user_found_ids), "should be", str(users_to_find_ids)])
        for i in users_to_find_ids:
            self.assertIn(i, user_found_ids, msg=msg)
        self.assertEqual(len(user_found_ids), len(users_to_find), msg=msg)

    def test_get_active_users_as_main_admin(self):
        # As a main admin, I can retrieve all users' full data
        response = self._get_users(True)
        users_to_find = [self.user1, self.user2, self.admin_user]
        self._check_users(response, users_to_find)

    def test_get_users_as_main_admin(self):
        # As a main admin, I can retrieve all users' full data
        response = self._get_users(False)
        users_to_find = [self.user1, self.user2, self.admin_user, self.user3]
        self._check_users(response, users_to_find)

    def test_create_user_with_password(self):
        data = dict(username="999999",
                    firstname="New",
                    lastname="USER",
                    email="new.user@aphp.fr",
                    password="password")
        request = self.factory.post(USERS_URL, data, format='json')
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'post': 'create'})(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", response.data)
        user = User.objects.get(pk=data["username"])
        self.assertTrue(user.password is not None)
        self.assertNotEqual(user.password, data["password"])    # password is hashed

    def test_create_user_without_password(self):
        data = dict(username="999999",
                    firstname="New",
                    lastname="USER",
                    email="new.user@aphp.fr")
        request = self.factory.post(USERS_URL, data, format='json')
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'post': 'create'})(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(pk=data["username"])
        self.assertTrue(user.password is None)

    def test_update_user_success(self):
        patch_data = dict(email="updated.email.address@aphp.fr")
        request = self.factory.patch(USERS_URL, patch_data, format='json')
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'patch': 'partial_update'})(request, username=self.user2.username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        user = User.objects.get(pk=self.user2.username)
        self.check_unupdatable_not_updated(user, self.user2)

    def test_delete_user_permission_denied(self):
        request = self.factory.delete(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'delete': 'destroy'})(request, username=self.user2.username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)
        user2 = User.objects.get(pk=self.user2.username)
        self.assertIsNotNone(user2)

    def test_check_user_exists_in_db(self):
        request = self.factory.get(f"{USERS_URL}/{self.user1.username}/check")
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'check_user_exists'})(request, username=self.user1.username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data
        self.assertTrue(result["already_exists"])
        self.assertFalse(result["found"])

    def test_check_user_exists_with_invalid_username(self):
        invalid_username = "!@#$%^&*()"
        request = self.factory.get(f"{USERS_URL}/{invalid_username}/check")
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'check_user_exists'})(request, username=invalid_username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('admin_cohort.views.users.users_service.try_hooks')
    def test_check_user_exists_found_using_hooks_success(self, mock_try_hooks):
        mock_try_hooks.return_value = {"username": "username",
                                       "firstname": "Firstname",
                                       "lastname": "LASTNAME",
                                       "email": "username.email@backend.com"
                                       }
        random_username = "1234567"
        request = self.factory.get(f"{USERS_URL}/{random_username}/check")
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'check_user_exists'})(request, username=random_username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data
        self.assertFalse(result["already_exists"])
        self.assertTrue(result["found"])

    @mock.patch('admin_cohort.views.users.users_service.try_hooks')
    def test_check_user_exists_not_found_using_hooks_success(self, mock_try_hooks):
        mock_try_hooks.return_value = None
        random_username = "1234567"
        request = self.factory.get(f"{USERS_URL}/{random_username}/check")
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'check_user_exists'})(request, username=random_username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('admin_cohort.views.users.users_service.try_hooks')
    def test_check_user_exists_hooks_error(self, mock_try_hooks):
        mock_try_hooks.side_effect = ServerError()
        random_username = "1234567"
        request = self.factory.get(f"{USERS_URL}/{random_username}/check")
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'check_user_exists'})(request, username=random_username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
