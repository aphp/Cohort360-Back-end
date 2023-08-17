from django.dispatch import Signal


onchange_allowed_users = Signal()


def manage_onchange_allowed_users(sender, **kwargs):
    print("************ allowed users changed!")
    operation = kwargs.get("operation")
    perimeter = kwargs.get("perimeter")
    user_id = kwargs.get("user_id")

    if operation == "add":
        print("************ add")
        add_new_allowed_user(perimeter=perimeter, user_id=user_id)
    elif operation == "revoke":
        print("************ revoke")
        revoke_user(perimeter=perimeter, user_id=user_id)


def add_new_allowed_user(perimeter, user_id: int):
    perimeter.allowed_users = list(set((perimeter.allowed_users or []) + [user_id]))
    perimeter.save()
    while perimeter.parent:
        allowed_users_inferior_levels = list(set((perimeter.allowed_users_inferior_levels or []) +
                                                 perimeter.allowed_users))
        parent = perimeter.parent
        parent_allowed_users_inferior_levels = parent.allowed_users_inferior_levels or []
        parent.allowed_users_inferior_levels = list(set(parent_allowed_users_inferior_levels +
                                                        allowed_users_inferior_levels))
        parent.save()
        perimeter = parent


def revoke_user(perimeter, user_id: int):
    perimeter.allowed_users.remove(user_id)
    perimeter.save()

    while perimeter.parent:
        parent = perimeter.parent
        remove_user = True
        for child in parent.children.all():
            if user_id in child.allowed_users + child.allowed_users_inferior_levels:
                remove_user = False
                break
        if remove_user:
            parent.allowed_users_inferior_levels.remove(user_id)
            parent.save()
        perimeter = parent
