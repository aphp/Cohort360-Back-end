from contextlib import contextmanager
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate

from accesses import permissions, porthab
from accesses.porthab import PorthabUnavailable, rights_from_groups
from accesses.services.accesses import accesses_service
from accesses.tests.base import AccessesAppTestsBase
from accesses.utils import impersonate_hook
from accesses.views import AccessViewSet
from admin_cohort.auth.auth_backends import OIDCAuthBackend
from admin_cohort.models import User
from admin_cohort.services.auth import auth_service
from admin_cohort.tools.cache import construct_cache_key

PREFIX = "/BBS_DA-N-EDS_DEV_APP_COHORT_"


@override_settings(PORTHAB_RIGHTS_ENABLED=True, PORTHAB_GROUP_PREFIX="EDS_DEV")
class PorthabRightsTests(AccessesAppTestsBase):
    def with_rights(self, user, *rights):
        user.porthab_rights = frozenset(rights)
        return user

    def test_rights_are_read_from_cohort_groups_only(self):
        groups = [
            f"{PREFIX}FULL_ADMIN",
            "BBS_DA-N-EDS_DEV_APP_COHORT_READ_DATALABS",
            "/BBS_DA-N-EDS_APP_COHORT_MANAGE_USERS",
            "/BBS_DA-N-EDS_DEV_APP_DATALAB_MANAGE_USERS",
            f"{PREFIX}UNKNOWN",
            "/BBS_DA-N-EDS_JUPYTERHUB",
        ]
        assert rights_from_groups(groups) == {"right_full_admin", "right_read_datalabs"}

    def test_porthab_full_admin_makes_a_full_admin(self):
        assert not accesses_service.user_is_full_admin(self.user_y)
        assert accesses_service.user_is_full_admin(self.with_rights(self.user_y, "right_full_admin"))

    def test_porthab_manage_users_allows_managing_users(self):
        user = self.with_rights(self.user_y, "right_manage_users")
        assert permissions.can_user_manage_users(user)
        assert permissions.can_user_manage_profiles(user)
        assert accesses_service.can_user_manage_users(user)

    def test_porthab_datalabs_rights(self):
        reader = self.with_rights(self.user_y, "right_read_datalabs")
        assert permissions.can_user_read_datalabs(reader)
        assert not permissions.can_user_manage_datalabs(reader)
        assert permissions.can_user_manage_datalabs(self.with_rights(self.user_z, "right_manage_datalabs"))

    def test_native_accesses_still_grant_their_rights(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_full_admin, perimeter=self.aphp)
        assert accesses_service.user_is_full_admin(self.with_rights(self.user_y))

    @mock.patch("accesses.utils.fetch_porthab_rights", return_value=frozenset())
    def test_porthab_full_admin_can_impersonate(self, _):
        impersonated = impersonate_hook(self.with_rights(self.user_y, "right_full_admin"), {"X-Impersonate": self.user_z.username})
        assert impersonated == self.user_z

    @mock.patch("accesses.utils.fetch_porthab_rights", return_value=frozenset())
    def test_impersonated_user_does_not_inherit_porthab_rights(self, _):
        impersonated = impersonate_hook(self.with_rights(self.user_y, "right_full_admin"), {"X-Impersonate": self.user_z.username})
        assert not accesses_service.user_is_full_admin(impersonated)

    def test_without_porthab_rights_impersonation_is_denied(self):
        with self.assertRaises(PermissionDenied):
            impersonate_hook(self.with_rights(self.user_y, "right_read_datalabs"), {"X-Impersonate": self.user_z.username})

    def test_my_accesses_lists_porthab_rights(self):
        request = APIRequestFactory().get("/accesses/accesses/my-accesses/")
        force_authenticate(request, user=self.with_rights(self.user_y, "right_manage_users"))
        response = AccessViewSet.as_view({"get": "get_my_accesses"})(request)
        assert response.status_code == 200
        porthab = [a for a in response.data if a["role"]["name"] == "Port'Hab"]
        assert len(porthab) == 1
        assert porthab[0]["role"]["right_manage_users"] is True
        assert porthab[0]["role"]["right_full_admin"] is False
        assert porthab[0]["is_valid"] is True

    def test_my_accesses_without_porthab_rights(self):
        request = APIRequestFactory().get("/accesses/accesses/my-accesses/")
        force_authenticate(request, user=self.user_y)
        response = AccessViewSet.as_view({"get": "get_my_accesses"})(request)
        assert not [a for a in response.data if a["role"]["name"] == "Port'Hab"]

    def test_cache_key_depends_on_porthab_rights(self):
        def key(user):
            request = mock.Mock(user=user, query_params={}, _request=mock.Mock(path="/x/"), spec=["user", "query_params", "_request"])
            return construct_cache_key(view_instance=self, view_method=self.test_cache_key_depends_on_porthab_rights, request=request)

        without = key(self.user_y)
        assert key(self.with_rights(self.user_y, "right_full_admin")) != without

    def authenticate(self, claims):
        oidc = mock.Mock(**{"authenticate.return_value": claims["preferred_username"], "decode_token.return_value": claims})
        with mock.patch.dict(auth_service.authenticators, {"OIDC": oidc}):
            return auth_service.authenticate_request(token="t", auth_method="OIDC", headers={})

    def test_oidc_request_carries_porthab_rights(self):
        claims = {"preferred_username": self.user_y.username, "groups": [f"{PREFIX}MANAGE_DATALABS"]}
        user, _ = self.authenticate(claims)
        assert user.porthab_rights == {"right_manage_datalabs"}

    @override_settings(PORTHAB_RIGHTS_ENABLED=False)
    def test_porthab_rights_are_ignored_when_disabled(self):
        claims = {"preferred_username": self.user_y.username, "groups": [f"{PREFIX}FULL_ADMIN"]}
        user, _ = self.authenticate(claims)
        assert not accesses_service.user_is_full_admin(user)


@override_settings(PORTHAB_RIGHTS_ENABLED=True, PORTHAB_GROUP_PREFIX="EDS_DEV")
class PorthabLoginTests(AccessesAppTestsBase):
    def login(self, claims):
        tokens = mock.Mock(access_token="t")
        with (
            mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.get_tokens", return_value=tokens),
            mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.decode_token", return_value=claims),
            mock.patch("admin_cohort.auth.auth_backends.oidc_auth_service.retrieve_username", return_value=claims["preferred_username"]),
        ):
            return OIDCAuthBackend().authenticate(mock.Mock(), code="c")

    def test_unknown_agent_with_cohort_group_is_created(self):
        user = self.login(
            {
                "preferred_username": "7000001",
                "given_name": "Camille",
                "family_name": "Martin",
                "email": "camille.martin@aphp.fr",
                "groups": [f"{PREFIX}READ_DATALABS"],
            }
        )
        assert user == User.objects.get(username="7000001")
        assert (user.firstname, user.lastname, user.email) == ("Camille", "Martin", "camille.martin@aphp.fr")

    def test_agents_without_email_are_created_without_email(self):
        for username in ("7000003", "7000004"):
            self.login({"preferred_username": username, "groups": [f"{PREFIX}READ_DATALABS"]})
        assert list(User.objects.filter(username__in=["7000003", "7000004"]).values_list("email", flat=True)) == [None, None]

    def test_an_email_already_taken_is_not_reused(self):
        User.objects.create(username="7000005", email="camille.martin@aphp.fr", delete_datetime=timezone.now())
        user = self.login({"preferred_username": "7000006", "email": "camille.martin@aphp.fr", "groups": [f"{PREFIX}READ_DATALABS"]})
        assert user.email is None

    def test_a_deleted_agent_with_cohort_group_is_reactivated(self):
        User.objects.create(username="7000007", email="dominique.petit@aphp.fr", delete_datetime=timezone.now())
        user = self.login({"preferred_username": "7000007", "groups": [f"{PREFIX}READ_DATALABS"]})
        assert user == User.objects.get(username="7000007")
        assert user.email == "dominique.petit@aphp.fr"

    def test_a_deleted_agent_without_cohort_group_stays_deleted(self):
        User.objects.create(username="7000008", delete_datetime=timezone.now())
        with self.assertRaises(User.DoesNotExist):
            self.login({"preferred_username": "7000008", "groups": ["/BBS_DA-N-EDS_JUPYTERHUB"]})

    def test_unknown_agent_without_cohort_group_is_refused(self):
        with self.assertRaises(User.DoesNotExist):
            self.login({"preferred_username": "7000002", "groups": ["/BBS_DA-N-EDS_JUPYTERHUB"]})
        assert not User.objects.filter(username="7000002").exists()


@override_settings(
    PORTHAB_RIGHTS_ENABLED=True,
    PORTHAB_GROUP_PREFIX="EDS_DEV",
    PORTHAB_API_URL="https://porthab.test",
    PORTHAB_SERVICE_TOKEN_URL="https://auth.test/realms/ID-Interne/protocol/openid-connect/token",
    PORTHAB_SERVICE_CLIENT_ID="cohort-noprod",
    PORTHAB_SERVICE_CLIENT_SECRET="secret",
)
class PorthabImpersonationTests(AccessesAppTestsBase):
    def setUp(self):
        super().setUp()
        cache.delete(porthab.SERVICE_ACCESS_CACHE_KEY)

    @contextmanager
    def porthab_replies(self, rights=(), status_code=200):
        token = mock.Mock(status_code=200, **{"json.return_value": {"access_token": "jeton", "expires_in": 300}})
        reply = mock.Mock(status_code=status_code, **{"json.return_value": {"rights": list(rights)}})
        with (
            mock.patch("accesses.porthab.requests.post", return_value=token) as post,
            mock.patch("accesses.porthab.requests.get", return_value=reply) as get,
        ):
            yield {"post": post, "get": get}

    def impersonate(self):
        admin = self.user_y
        admin.porthab_rights = frozenset({"right_full_admin"})
        return impersonate_hook(admin, {"X-Impersonate": self.user_z.username})

    def test_impersonated_user_gets_his_own_porthab_rights(self):
        with self.porthab_replies(["cohort.manage_users", "cohort.search_ipp", "datalab.lire"]) as doubles:
            impersonated = self.impersonate()
        assert impersonated.porthab_rights == {"right_manage_users"}
        doubles["get"].assert_called_once()
        assert doubles["get"].call_args.args[0] == f"https://porthab.test/api/v1/applications/agents/{self.user_z.username}/rights/"
        assert doubles["get"].call_args.kwargs["headers"] == {"Authorization": "Bearer jeton"}

    def test_impersonation_falls_back_to_native_accesses_when_porthab_is_unreachable(self):
        with self.porthab_replies(status_code=503):
            impersonated = self.impersonate()
        assert impersonated == self.user_z
        assert impersonated.porthab_rights == frozenset()

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_a_rejected_service_token_is_requested_again(self):
        with self.porthab_replies(status_code=401) as doubles:
            for _ in range(2):
                with self.assertRaises(PorthabUnavailable):
                    porthab.fetch_porthab_rights(self.user_z.username)
        assert doubles["post"].call_count == 2

    @override_settings(PORTHAB_RIGHTS_ENABLED=False)
    def test_porthab_is_not_called_when_disabled(self):
        self.create_new_access_for_user(profile=self.profile_y, role=self.role_full_admin, perimeter=self.aphp)
        with self.porthab_replies() as doubles:
            impersonate_hook(self.user_y, {"X-Impersonate": self.user_z.username})
        doubles["get"].assert_not_called()

    def test_username_is_encoded_in_the_porthab_url(self):
        with self.porthab_replies() as doubles:
            porthab.fetch_porthab_rights("../../admin")
        assert doubles["get"].call_args.args[0] == "https://porthab.test/api/v1/applications/agents/..%2F..%2Fadmin/rights/"
