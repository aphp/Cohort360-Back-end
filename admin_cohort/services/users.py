import hashlib
import os
import re
from typing import Optional

import requests
from django.conf import settings
from django.http import Http404
from rest_framework import status

from accesses.models import Profile
from admin_cohort.types import PersonIdentity
from admin_cohort.exceptions import ServerError

env = os.environ

USERNAME_REGEX = env.get("USERNAME_REGEX", "(.*)")


class UsersService:

    def validate_user_data(self, data: dict):
        if settings.IDENTITY_SERVER_USER_INFO_ENDPOINT:
            self.verify_user_identity(username=data.get("username"))
        self.check_fields_against_regex(data=data)
        self.hash_password(data=data)

    @staticmethod
    def verify_user_identity(username: str) -> Optional[PersonIdentity]:
        response = requests.post(url=settings.IDENTITY_SERVER_USER_INFO_ENDPOINT,
                                 data={'username': username},
                                 headers=settings.ID_CHECKER_HEADERS)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise Http404
        if response.status_code != status.HTTP_200_OK:
            raise ServerError(f"Error from ID-CHECKER server: {response.text}")
        res = response.json().get('data', {}).get('attributes', {})
        try:
            return PersonIdentity(firstname=res['givenName'],
                                  lastname=res['sn'],
                                  username=res['cn'],
                                  email=res['mail'])
        except KeyError as ke:
            raise ServerError(f"Missing field in ID-CHECKER response {res} - {ke}")

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
    def hash_password(data: dict) -> None:
        password = data.get("password")
        if password is not None:
            hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
            data["password"] = hashed

    @staticmethod
    def create_initial_profile(data: dict) -> None:
        Profile.objects.create(user_id=data.get("username"), is_active=True)

    def check_user_existence(self, username: str) -> Optional[PersonIdentity]:
        if not (username and re.compile(USERNAME_REGEX).match(username)):
            raise ValueError("Invalid username format")
        return self.verify_user_identity(username=username)


users_service = UsersService()
