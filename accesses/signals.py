from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from accesses.models import Access, get_user_valid_manual_accesses
from accesses.tasks import add_new_allowed_user, revoke_user


@receiver(signal=post_save, sender=Access, dispatch_uid="manage_onchange_allowed_users")
def manage_onchange_allowed_users(sender, **kwargs):
    access = kwargs.get("instance")
    is_new_access = kwargs.get("created")
    is_closed_or_invalid_access = not kwargs.get("created") and (access.end_datetime < timezone.now()
                                                                 or kwargs.get("invalid"))
    perimeter_id = access.perimeter_id
    user_id = access.profile.user_id

    if is_new_access:
        add_new_allowed_user.delay(perimeter_id, user_id)
    elif is_closed_or_invalid_access:
        extra_accesses_on_perimeter = get_user_valid_manual_accesses(user=access.profile.user) \
                                      .filter(perimeter_id=access.perimeter_id) \
                                      .exists()
        if not extra_accesses_on_perimeter:
            revoke_user.delay(perimeter_id, user_id)
