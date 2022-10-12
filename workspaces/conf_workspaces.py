import json
from typing import Dict, List

import environ
import requests
import simplejson
from requests import Response
from rest_framework import status

from admin_cohort.models import User

env = environ.Env()
INFRA_AD_TOKEN = env('INFRA_AD_TOKEN')
INFRA_API_URL = f"{env('INFRA_API_URL')}"
ACTIVE_DIRECTORY_URL = f"{INFRA_API_URL}/active_directory"
USER_GROUPS_URL = f"{ACTIVE_DIRECTORY_URL}/get_user_groups"
ACTIVE_DIRECTORY_PARENT_GROUP = env('ACTIVE_DIRECTORY_PARENT_GROUP')


def check_resp(resp: Response, url: str) -> Dict:
    if resp.status_code not in [status.HTTP_201_CREATED, status.HTTP_200_OK]:
        raise Exception(f"Connection error with Infr API ({url}) : "
                        f"status code {resp.text}")

    try:
        res = resp.json()
    except (simplejson.JSONDecodeError, json.JSONDecodeError, ValueError):
        raise Exception(f"Response from Infra API ({url}) not readable: "
                        f"status code {resp.status_code} - "
                        f"{resp.text}")

    if not isinstance(res, List) or not all([isinstance(s, str) for s in res]):
        raise Exception(f"Format of response from Infra API ({url}) not "
                        f"expected (expected list of str) : "
                        f"status code {resp.status_code} - "
                        f"{resp.text}")

    return res


def is_user_bound_to_unix_account(user: User, unix_acc_group: str) -> bool:
    resp = requests.get(
        f"{INFRA_API_URL}/active_directory/is_member_of_group",
        params={
            'id_aph': user.provider_username,
            'group_dn': unix_acc_group,
        }, headers={'auth-token': INFRA_AD_TOKEN}
    )

    if resp.status_code != status.HTTP_200_OK:
        raise Exception(f"INTERNAL ERROR, request to infra API failed "
                        f"({resp.status_code}): {resp.text}")
    else:
        b = resp.json()
        if not isinstance(b, bool):
            raise Exception(f"INTERNAL ERROR, response from "
                            f"infra API unexpected (should be boolean):"
                            f" {resp.text}")
        return b


def get_account_groups_from_id_aph(id_aph: str) -> List[str]:
    resp = requests.get(params={
        'parent_dn': ACTIVE_DIRECTORY_PARENT_GROUP,
        'id_aph': id_aph,
    }, headers={'auth-token': INFRA_AD_TOKEN}, url=USER_GROUPS_URL)

    res = check_resp(resp, USER_GROUPS_URL)

    return res
