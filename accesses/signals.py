from itertools import chain

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accesses.models import Access, get_user_valid_manual_accesses, Perimeter


@receiver(signal=post_save, sender=Access, dispatch_uid="manage_onchange_allowed_users")
def manage_onchange_allowed_users(sender, **kwargs):
    access = kwargs.get("instance")
    is_new_access = kwargs.get("created")
    is_closed_or_invalid_access = not kwargs.get("created") and (access.end_datetime < timezone.now()
                                                                 or kwargs.get("invalid"))
    perimeter = access.perimeter
    user_id = access.profile.user_id

    if is_new_access:
        add_new_allowed_user(perimeter=perimeter, user_id=user_id)
        add_user_to_parent_perimeters(perimeter=perimeter, user_id=user_id)
        add_user_to_child_perimeters(perimeter=perimeter, user_id=user_id)
    elif is_closed_or_invalid_access:
        revoke_user(closed_access=access, perimeter=perimeter, user_id=user_id)


def add_new_allowed_user(perimeter, user_id: int):
    perimeter.allowed_users = list(set((perimeter.allowed_users or []) + [user_id]))
    perimeter.save()


def add_user_to_parent_perimeters(perimeter: Perimeter, user_id: int):
    parent = perimeter.parent
    if parent:
        allowed_users_inferior_levels = parent.allowed_users_inferior_levels or []
        parent.allowed_users_inferior_levels = list(set(allowed_users_inferior_levels + [user_id]))
        parent.save()
        if parent.parent:
            add_user_to_parent_perimeters(perimeter=parent, user_id=user_id)


def add_user_to_child_perimeters(perimeter: Perimeter, user_id: int):
    for child in perimeter.children.all():
        allowed_users_above_levels = child.allowed_users_above_levels or []
        child.allowed_users_above_levels = list(set(allowed_users_above_levels + [user_id]))
        child.save()
        if child.children.all():
            add_user_to_child_perimeters(perimeter=child, user_id=user_id)


def revoke_user(closed_access: Access, perimeter: Perimeter, user_id: int):
    extra_accesses_on_perimeter = get_user_valid_manual_accesses(user=closed_access.profile.user)\
                                  .filter(perimeter_id=closed_access.perimeter_id)\
                                  .exists()

    if not extra_accesses_on_perimeter:
        try:
            perimeter.allowed_users.remove(user_id)
            perimeter.save()
        except ValueError:
            return
        revoke_user_from_parent_perimeters(perimeter=perimeter, user_id=user_id)
        revoke_user_from_child_perimeters(perimeter=perimeter, user_id=user_id)


def revoke_user_from_parent_perimeters(perimeter: Perimeter, user_id: int):
    parent = perimeter.parent
    for child in parent.children.all():
        if user_id in chain(child.allowed_users,
                            child.allowed_users_inferior_levels):
            return
    try:
        parent.allowed_users_inferior_levels.remove(user_id)
        parent.save()
    except ValueError:
        pass
    if parent.parent:
        revoke_user_from_parent_perimeters(perimeter=parent, user_id=user_id)


def revoke_user_from_child_perimeters(perimeter: Perimeter, user_id: int):
    if user_id not in chain(perimeter.allowed_users,
                            perimeter.allowed_users_above_levels):
        for child in perimeter.children.all():
            try:
                child.allowed_users_above_levels.remove(user_id)
                child.save()
            except ValueError:
                pass
            if child.children.all():
                revoke_user_from_child_perimeters(perimeter=child, user_id=user_id)
