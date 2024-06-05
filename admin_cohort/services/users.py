import re
from typing import Optional

import requests
from environ import environ
from rest_framework import status

from admin_cohort.models import User
from admin_cohort.types import PersonIdentity, ServerError, MissingDataError

env = environ.Env()

ID_CHECKER_URL = env("ID_CHECKER_URL")
ID_CHECKER_TOKEN_HEADER = env("ID_CHECKER_TOKEN_HEADER")
ID_CHECKER_TOKEN = env("ID_CHECKER_TOKEN")
ID_CHECKER_SERVER_HEADERS = {ID_CHECKER_TOKEN_HEADER: ID_CHECKER_TOKEN}
USERNAME_REGEX = env("USERNAME_REGEX")


class UsersService:

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

    def check_existing_user(self, username: str):
        if not (username and re.compile(USERNAME_REGEX).match(username)):
            raise ValueError("The given username format is not allowed")
        person = self.verify_identity(username)
        user = User.objects.filter(username=person.user_id).first()
        # manual_profile = Profile.objects.filter(Profile.q_is_valid()
        #                                         & Q(source=MANUAL_SOURCE)
        #                                         & Q(user_id=person.user_id)).first()
        return {"firstname": person.firstname,
                "lastname": person.lastname,
                "email": person.email,
                "username": username,
                "user": user,
                # "manual_profile": manual_profile
                }


users_service = UsersService()
