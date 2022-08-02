from typing import List

from admin_cohort.models import User


def get_user_groups(id_aph: str) -> List[str]:
    """
    For a given user id, should return a list of Unix accounts defining strs
    @param id_aph:
    @return:
    """
    raise NotImplementedError()


def get_account_groups_from_id_aph(id_aph: str) -> List[str]:
    raise NotImplementedError()


def is_user_bound_to_unix_account(user: User, unix_acc_group: str) -> bool:
    raise NotImplementedError()
