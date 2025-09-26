import logging
import os
import hashlib
import re
from typing import Optional

from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework.exceptions import APIException

from accesses.models import Profile
from accesses.services.accesses_syncer import AccessesSynchronizer
from admin_cohort.apps import AdminCohortConfig

logger = logging.getLogger(__name__)


class UsersService:

    def validate_user_data(self, data: dict):
        self.check_fields_against_regex(data=data)
        if "password" in data:
            data["password"] = self.hash_password(data["password"])

    @staticmethod
    def check_fields_against_regex(data: dict) -> None:
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")

        assert all(f and isinstance(f, str) for f in (firstname, lastname, email)), "Basic info fields must be strings"

        name_regex = re.compile(r"^[\wÀ-ÖØ-öø-ÿ' -]*$")
        email_regex = re.compile(settings.EMAIL_REGEX)

        if firstname and lastname and not name_regex.match(f"{firstname + lastname}"):
            raise ValueError("Invalid firstname/lastname: may contain only letters and `'-`")
        if email and not email_regex.match(email):
            raise ValueError(f"Invalid email address {email}: may be only alphanumeric or contain `@_-.`")

    @staticmethod
    def hash_password(password: str) -> str:
        if password is not None:
            return hashlib.sha256(password.encode("utf-8")).hexdigest()
        raise ValueError("Password cannot be None")

    @staticmethod
    def setup_profile(data: dict) -> None:
        user_id = data.get("username")
        Profile.objects.create(user_id=user_id, is_active=True)
        if os.environ.get("SYNC_USER_ACCESSES", False):
            AccessesSynchronizer().sync_accesses(target_user=user_id)

    @staticmethod
    def try_hooks(username: str) -> Optional[dict]:
        check_identity_hooks = AdminCohortConfig.HOOKS.get("USER_IDENTITY", [])
        for check_identity_hook in check_identity_hooks:
            try:
                check_user_identity = import_string(check_identity_hook)
                user_identity = check_user_identity(username=username)
                if user_identity is not None:
                    return user_identity
            except ImportError as e:
                logger.error(f"[User Identity Check] hook improperly configured: {str(e)}")
            except APIException as e:
                logger.error(f"[User Identity Check] Error: {str(e)}")
                continue
        logger.error("[User Identity Check] All hooks failed. Review or remove them")
        return None


users_service = UsersService()
