import logging
import re
from typing import Optional

import requests
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from environ import environ
from rest_framework import status

from accesses.models import Profile
from admin_cohort.models import User
from admin_cohort.settings import MANUAL_SOURCE
from admin_cohort.types import PersonIdentity, ServerError, MissingDataError

env = environ.Env()

ID_CHECKER_URL = env("ID_CHECKER_URL")
ID_CHECKER_TOKEN_HEADER = env("ID_CHECKER_TOKEN_HEADER")
ID_CHECKER_TOKEN = env("ID_CHECKER_TOKEN")
ID_CHECKER_SERVER_HEADERS = {ID_CHECKER_TOKEN_HEADER: ID_CHECKER_TOKEN}

USERNAME_REGEX = env("USERNAME_REGEX")

_logger = logging.getLogger("django.request")


class ProfilesService:

    @staticmethod
    def verify_identity(id_aph: str) -> Optional[PersonIdentity]:
        response = requests.post(url=ID_CHECKER_URL,
                                 data={'username': id_aph},
                                 headers=ID_CHECKER_SERVER_HEADERS)
        if status.is_server_error(response.status_code):
            raise ServerError(f"Error {response.status_code} from ID-CHECKER server ({ID_CHECKER_URL}): {response.text}")
        if response.status_code != status.HTTP_200_OK:
            raise ServerError(f"Internal error: {response.text}")

        res: dict = response.json().get('data', {}).get('attributes', {})
        for expected in ['givenName', 'sn', 'cn', 'mail']:
            if expected not in res:
                raise MissingDataError(f"ID-CHECKER server response is missing {expected} ({response.content})")
        return PersonIdentity(firstname=res.get('givenName'),
                              lastname=res.get('sn'),
                              user_id=res.get('cn'),
                              email=res.get('mail'))

    def check_existing_profile(self, username: str):
        if not username:
            raise ValueError("No `username` was provided")
        if not re.compile(USERNAME_REGEX).match(username):
            raise ValueError("The given username format is not allowed")
        person = self.verify_identity(username)
        user = User.objects.filter(username=person.user_id).first()
        manual_profile = Profile.objects.filter(Profile.q_is_valid()
                                                & Q(source=MANUAL_SOURCE)
                                                & Q(user_id=person.user_id)).first()
        return {"firstname": person.firstname,
                "lastname": person.lastname,
                "user_id": person.user_id,
                "email": person.email,
                "provider": user,
                "user": user,
                "manual_profile": manual_profile}

    @staticmethod
    def check_fields_against_regex(data: dict) -> None:
        firstname = data.get("firstname")
        lastname = data.get("lastname")
        email = data.get("email")

        assert all([f and isinstance(f, str) for f in (firstname, lastname, email)]), "Basic info fields must be strings"

        name_regex_pattern = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ\-' ]*$")
        email_regex_pattern = re.compile(r"^[A-Za-z0-9\-. @_]*$")

        if firstname and lastname and not name_regex_pattern.match(f"{firstname + lastname}"):
            raise ValidationError("Le nom/prénom fourni est invalide. Doit comporter "
                                  "uniquement des lettres et des caractères ' et - ")
        if email and not email_regex_pattern.match(email):
            raise ValidationError(f"L'adresse email fournie ({email}) est invalide. Doit comporter "
                                  f"uniquement des lettres, chiffres et caractères @_-.")

    @staticmethod
    def fix_profile_entries(data: dict, for_create: bool = False) -> None:
        is_active = data.get("is_active")
        valid_start_datetime = data.get("valid_start_datetime")
        valid_end_datetime = data.get("valid_end_datetime")

        if for_create:
            now = timezone.now()
            data["manual_is_active"] = True
            data["valid_start_datetime"] = now
            data["manual_valid_start_datetime"] = now

        if is_active is not None:
            data["manual_is_active"] = is_active
        if valid_start_datetime:
            data["manual_valid_start_datetime"] = valid_start_datetime
        if valid_end_datetime:
            data["manual_valid_end_datetime"] = valid_end_datetime

    def process_creation_data(self, data: dict) -> None:
        user_id = data.get("user_id")
        assert user_id, "Must provide `user_id` to create a new profile"

        self.verify_identity(user_id)
        self.check_fields_against_regex(data)
        self.fix_profile_entries(data, for_create=True)

        user = User.objects.create(firstname=data.get('firstname'),
                                   lastname=data.get('lastname'),
                                   email=data.get('email'),
                                   username=user_id,
                                   provider_id=user_id)
        data.update({'provider_name': f"{user.firstname} {user.lastname}",
                     'provider_id': user_id})

    def process_patch_data(self, data: dict) -> None:
        self.check_fields_against_regex(data=data)
        self.fix_profile_entries(data=data)


profiles_service = ProfilesService()
