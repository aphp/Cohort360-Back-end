import logging
from typing import Optional

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from accesses.porthab import rights_from_groups

from admin_cohort.services.auth import jwt_auth_service, oidc_auth_service
from admin_cohort.models import User

logger = logging.getLogger(__name__)


class BaseAuthBackend:
    def get_user(self, user_id) -> Optional[User]:
        return User.objects.get(username=user_id)


class JWTAuthBackend(BaseAuthBackend):
    def authenticate(self, request, username, password):
        # param 'request' is forced by function signature in the definition of the AuthBackend. DO NOT REMOVE!
        _ = request
        valid_credentials = jwt_auth_service.check_credentials(username=username, password=password)
        if valid_credentials:
            return self.get_user(user_id=username)
        raise AuthenticationFailed("Invalid username or password!")


class OIDCAuthBackend(BaseAuthBackend):
    def authenticate(self, request, code, redirect_uri: Optional[str] = None):
        auth_tokens = oidc_auth_service.get_tokens(code=code, redirect_uri=redirect_uri)
        if auth_tokens is None:
            raise AuthenticationFailed("Invalid username or password")
        request.auth_tokens = auth_tokens
        username = oidc_auth_service.retrieve_username(token=auth_tokens.access_token)
        if settings.PORTHAB_RIGHTS_ENABLED:
            return self.porthab_user(username, auth_tokens.access_token)
        return self.get_user(user_id=username)

    def porthab_user(self, username: str, access_token: str) -> Optional[User]:
        known = User.objects.all(even_deleted=True).filter(username=username).first()
        if known is not None and known.delete_datetime is None:
            return known
        claims = oidc_auth_service.decode_token(token=access_token, verify_signature=False)
        if not rights_from_groups(claims.get("groups", [])):
            return self.get_user(user_id=username)
        if known is not None:
            logger.info(f"{username} réactivé par ses droits Port'Hab")
            known.delete_datetime = None
            known.save()
            return known
        email = claims.get("email") or None
        if email and User.objects.all(even_deleted=True).filter(email=email).exists():
            logger.warning(f"Email déjà porté par un autre compte, {username} est créé sans email")
            email = None
        return User.objects.create(
            username=username,
            firstname=claims.get("given_name", ""),
            lastname=claims.get("family_name", ""),
            email=email,
        )
