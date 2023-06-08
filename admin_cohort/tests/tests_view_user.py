from rest_framework import status
from rest_framework.test import force_authenticate

from accesses.models import Access, Role, Perimeter, Profile
from admin_cohort.models import User
from admin_cohort.settings import PERIMETERS_TYPES, MANUAL_SOURCE
from admin_cohort.tools.tests_tools import BaseTests
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
        self.aphp = Perimeter.objects.create(**dict(local_id=1,
                                                    name="APHP",
                                                    parent=None,
                                                    type_source_value=PERIMETERS_TYPES[0],
                                                    source_value="APHP"))
        self.hospital1 = Perimeter.objects.create(**dict(local_id=11,
                                                         name="Hospital 01",
                                                         parent=self.aphp,
                                                         type_source_value=PERIMETERS_TYPES[2],
                                                         source_value="Hospital 01"))
        self.hospital2 = Perimeter.objects.create(**dict(local_id=12,
                                                         name="Hospital 02",
                                                         parent=self.aphp,
                                                         type_source_value=PERIMETERS_TYPES[2],
                                                         source_value="Hospital 02"))
        self.hospital3 = Perimeter.objects.create(**dict(local_id=13,
                                                         name="Hospital 03",
                                                         parent=self.aphp,
                                                         type_source_value=PERIMETERS_TYPES[2],
                                                         source_value="Hospital 03"))

        self.main_admin_role = Role.objects.create(**dict([(f, True) for f in self.all_rights]), name='Admin full role')
        self.admin_role = Role.objects.create(**dict([(f, True) for f in self.all_rights]), name='Admin role')
        self.pseudo_anonymised_data_role = Role.objects.create(**dict([(f, True) for f in self.all_rights]), name='Pseudo anonymised data role')

        self.admin_user = User.objects.create(provider_username="000000", firstname="Admin", lastname="ADMIN", email="admin@aphp.fr")
        self.user1 = User.objects.create(provider_username="1111111", firstname="User 01", lastname="USER01", email="user01@aphp.fr")
        self.user2 = User.objects.create(provider_username="2222222", firstname="User 02", lastname="USER02", email="user02@aphp.fr")

        self.admin_profile = Profile.objects.create(source=MANUAL_SOURCE, user=self.admin_user, manual_is_active=True)
        self.profile1 = Profile.objects.create(source=MANUAL_SOURCE, user=self.user1, manual_is_active=True)
        self.profile2 = Profile.objects.create(source=MANUAL_SOURCE, user=self.user2, manual_is_active=True)

        self.admin_access = Access.objects.create(perimeter_id=self.aphp.id,
                                                  role=self.main_admin_role,
                                                  profile=self.admin_profile)
        self.access_user1_admin_h1 = Access.objects.create(perimeter_id=self.hospital1.id,
                                                           role=self.admin_role,
                                                           profile=self.profile1)
        self.access_user2_admin_h2 = Access.objects.create(perimeter_id=self.hospital2.id,
                                                           role=self.admin_role,
                                                           profile=self. profile2)
        self.access_user1_pseudo_h3 = Access.objects.create(perimeter_id=self.hospital3.id,
                                                            role=self.pseudo_anonymised_data_role,
                                                            profile=self. profile1)


class UserTestsAsAdmin(UserTests):
    unupdatable_fields = ["provider_name", "last_login_datetime", "source"]
    unsettable_default_fields = dict(last_login_datetime=None, source=None)
    unsettable_fields = ["provider_id"]

    def test_get_provider_as_main_admin(self):
        # As a main admin, I can get a user's full data
        request = self.factory.get(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'retrieve'})(request, provider_username=self.user1.provider_username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        user_found = ObjectView(self.get_response_payload(response))
        self.assertEqual(user_found.provider_username, self.user1.provider_username)
        self.assertEqual(user_found.email, self.user1.email)

    def test_get_users_as_main_admin(self):
        # As a main admin, I can retrieve all users' full data
        request = self.factory.get(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'get': 'list'})(request)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        users_to_find = [self.user1, self.user2, self.admin_user]
        users_found = [ObjectView(u) for u in self.get_response_payload(response)["results"]]

        user_found_ids = [p.provider_username for p in users_found]
        users_to_find_ids = [p.provider_username for p in users_to_find]
        msg = "\n".join(["", "got", str(user_found_ids), "should be", str(users_to_find_ids)])
        for i in users_to_find_ids:
            self.assertIn(i, user_found_ids, msg=msg)
        self.assertEqual(len(user_found_ids), len(users_to_find), msg=msg)

    def test_update_provider_as_main_admin(self):
        # As a main admin, I cannot update a user's manual data
        data = dict(firstname="Squall",
                    lastname="Leonheart",
                    email="s.l@aphp.fr",
                    perimeter_id=self.hospital1.id)
        request = self.factory.patch(USERS_URL, data, format='json')
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'patch': 'partial_update'})(request, provider_username=self.user2.provider_username)
        response.render()
        # self.assertEqual(response.status_code, status.HTTP_200_OK,
        # response.content)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)
        user = User.objects.get(pk=self.user2.provider_username)
        self.check_unupdatable_not_updated(user, self.user2)

    def test_delete_user_as_main_admin(self):
        # As a main admin, I can delete a user
        request = self.factory.delete(USERS_URL)
        force_authenticate(request, self.admin_user)
        response = UserViewSet.as_view({'delete': 'destroy'})(request, provider_username=self.user2.provider_username)
        response.render()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)
        user = User.objects.filter(provider_id=self.user2.provider_username).first()
        self.assertIsNone(user)
