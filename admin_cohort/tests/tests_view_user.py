from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import force_authenticate

from accesses.models import Access
from admin_cohort.models import User
from admin_cohort.settings import utc
from admin_cohort.tests_tools import BaseTests
from admin_cohort.views import UserViewSet

USERS_URL = "/users"


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
        self.admin_access = Access.objects.create(
            perimeter_id=self.aphp.id,
            role=self.main_admin_role,
            profile=self.admin_profile,
        )
        self.access_user1_admin_h1 = Access.objects.create(
            perimeter_id=self.hospital1.id,
            role=self.admin_role,
            profile=self.profile1,
        )
        self.access_user1_pseudo_h3 = Access.objects.create(
            perimeter_id=self.hospital3.id,
            role=self.pseudo_anonymised_data_role,
            profile=self. profile1,
        )
        self.access_user2_admin_h2 = Access.objects.create(
            care_site_history_id=3,
            perimeter_id=self.hospital2.id,
            role=self.admin_role,
            profile=self. profile2,
        )


class UserTestsAsAdmin(UserTests):
    unupdatable_fields = [
        "provider_name",
        "last_login_datetime",
        "creation_datetime",
        "modified_datetime",
        "change_datetime",
        "source",
    ]
    unsettable_default_fields = dict(
        last_login_datetime=None,
        creation_datetime=None,
        modified_datetime=None,
        source=None,
    )
    unsettable_fields = [
        "provider_id",
        "change_datetime",
    ]

    def test_error_create_provider_as_main_admin(self):
        # As a main admin, I can create an admin access for user1 to hospital2
        request_user = dict(
            provider_source_value="50",
            birth_date=utc.localize(datetime.now() + timedelta(days=-20)),
            firstname="Squall",
            lastname="Leonheart",
            email="s.l@aphp.fr",
            perimeter_id=self.hospital1.id,
        )
        request = self.factory.post('/users', request_user, format='json')
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'post': 'create'})(request)
        response.render()
        # self.assertEqual(response.status_code, status.HTTP_201_CREATED,
        # response.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.content)
        user = User.objects.filter(
            provider_source_value=request_user["provider_source_value"],
        ).first()
        self.assertIsNone(user)
        # self.check_is_created(user, self.admin_provider, request_user)

    def test_get_provider_as_main_admin(self):
        # As a main admin, I can get a user's full data
        request = self.factory.get(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'retrieve'})(
            request,
            provider_username=self.user1.provider_username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         response.content)
        user_found = ObjectView(self.get_response_payload(response))
        self.assertEqual(user_found.provider_username,
                         self.user1.provider_username)
        self.assertEqual(user_found.email, self.user1.email)

    def test_get_users_as_main_admin(self):
        # As a main admin, I can retrieve all users' full data
        request = self.factory.get(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'list'})(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         response.content)
        providers_to_find = [self.user1, self.user2,
                             self.admin_user]

        providers_found = [ObjectView(u) for u
                           in self.get_response_payload(response)["results"]]

        user_found_ids = [p.provider_username for p in providers_found]
        providers_to_find_ids = [p.provider_id for p in providers_to_find]
        msg = "\n".join(["", "got", str(user_found_ids), "should be",
                         str(providers_to_find_ids)])
        for i in providers_to_find_ids:
            self.assertIn(i, user_found_ids, msg=msg)
        self.assertEqual(len(user_found_ids), len(providers_to_find), msg=msg)

    def test_update_provider_as_main_admin(self):
        # As a main admin, I cannot update a user's manual data
        request = self.factory.patch(USERS_URL, dict(
            firstname="Squall",
            lastname="Leonheart",
            email="s.l@aphp.fr",
            perimeter_id=self.hospital1.id,
        ), format='json')
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'patch': 'partial_update'})(
            request, provider_username=self.user2.provider_username)

        response.render()
        # self.assertEqual(response.status_code, status.HTTP_200_OK,
        # response.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.content)
        user = User.objects.get(pk=self.user2.provider_username)
        self.check_unupdatable_not_updated(user, self.user2)

    def test_delete_provider_as_main_admin(self):
        # As a main admin, I cannot delete a user
        request = self.factory.delete(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'delete': 'destroy'})(
            request,
            provider_username=self.user2.provider_username
        )

        response.render()
        # self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT,
        # response.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN,
                         response.content)
        provider = User.objects.filter(
            # even_deleted=True,
            provider_id=self.user2.provider_username
        ).first()
        self.assertIsNotNone(provider)
        # self.check_is_deleted(provider, self.admin_provider)
