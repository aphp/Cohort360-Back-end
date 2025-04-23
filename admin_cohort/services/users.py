import logging
import os
import re
from typing import Optional

import requests
from django.http import Http404
from rest_framework import status

from accesses.models import Profile
from accesses.services.accesses_syncer import AccessesSynchronizer
from admin_cohort.types import PersonIdentity, ServerError

env = os.environ

ID_CHECKER_URL = f"{env.get('ID_CHECKER_URL')}/user/info"
ID_CHECKER_TOKEN_HEADER = env.get("ID_CHECKER_TOKEN_HEADER")
ID_CHECKER_TOKEN = env.get("ID_CHECKER_TOKEN")
ID_CHECKER_SERVER_HEADERS = {ID_CHECKER_TOKEN_HEADER: ID_CHECKER_TOKEN}

USERNAME_REGEX = env.get("USERNAME_REGEX", "(.*)")

_logger = logging.getLogger("info")


class UsersService:

    def validate_user_data(self, data: dict):
        if ID_CHECKER_URL is not None:
            self.verify_user_identity(username=data.get("username"))
        self.check_fields_against_regex(data=data)

    @staticmethod
    def verify_user_identity(username: str) -> Optional[PersonIdentity]:
        response = requests.post(url=ID_CHECKER_URL,
                                 data={'username': username},
                                 headers=ID_CHECKER_SERVER_HEADERS)
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

        name_regex = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\-' ]*$")
        email_regex = re.compile(r"^[A-Za-z0-9\-. @_]*$")

        if firstname and lastname and not name_regex.match(f"{firstname + lastname}"):
            raise ValueError("Nom/Prénom invalide. Doit comporter uniquement des lettres et des caractères ' et - ")
        if email and not email_regex.match(email):
            raise ValueError(f"Adresse email invalide: {email}. Doit comporter uniquement des lettres, chiffres et caractères @_-.")

    @staticmethod
    def setup_profile(data: dict) -> None:
        user_id = data.get("username")
        Profile.objects.create(user_id=user_id, is_active=True)
        if env.get("SYNC_USER_ORBIS_ACCESSES", False):
            AccessesSynchronizer().sync_accesses(target_user=user_id)

    def check_user_existence(self, username: str) -> Optional[PersonIdentity]:
        if not (username and re.compile(USERNAME_REGEX).match(username)):
            raise ValueError("Invalid username format")
        return self.verify_user_identity(username=username)


users_service = UsersService()
