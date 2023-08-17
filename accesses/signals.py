from django.dispatch import Signal


onchange_allowed_users = Signal()


def manage_onchange_allowed_users(sender, **kwargs):
    operation = kwargs.get("operation")
    perimeter = kwargs.get("perimeter")
    user_id = kwargs.get("user_id")

    if operation == "add":
        add_new_allowed_user(perimeter=perimeter, user_id=user_id)
    elif operation == "revoke":
        revoke_user(perimeter=perimeter, user_id=user_id)


def add_new_allowed_user(perimeter, user_id: int):
    perimeter.allowed_users = list(set((perimeter.allowed_users or []) + [user_id]))
    perimeter.save()
    add_user_to_parent_perimeters(perimeter=perimeter, user_id=user_id)
    add_user_to_child_perimeters(perimeter=perimeter, user_id=user_id)


def add_user_to_parent_perimeters(perimeter, user_id):
    parent = perimeter.parent
    if parent:
        parent.allowed_users_inferior_levels = list(set((parent.allowed_users_inferior_levels or []) + [user_id]))
        parent.save()
        if parent.parent:
            add_user_to_parent_perimeters(perimeter=parent, user_id=user_id)


def add_user_to_child_perimeters(perimeter, user_id):
    for child in perimeter.children.all():
        allowed_users_above_levels = child.allowed_users_above_levels or []
        child.allowed_users_above_levels = list(set(allowed_users_above_levels + [user_id]))
        child.save()
        if child.children.all():
            revoke_user_from_child_perimeters(perimeter=child, user_id=user_id)


def revoke_user(perimeter, user_id: int):
    try:
        perimeter.allowed_users.remove(user_id)
        perimeter.save()
    except ValueError:
        return
    revoke_user_from_parent_perimeters(perimeter=perimeter, user_id=user_id)

    if user_id not in perimeter.allowed_users_above_levels:
        revoke_user_from_child_perimeters(perimeter=perimeter, user_id=user_id)


def revoke_user_from_parent_perimeters(perimeter, user_id: int):
    parent = perimeter.parent
    for child in parent.children.all():
        if user_id in child.allowed_users + child.allowed_users_inferior_levels:
            return
    try:
        parent.allowed_users_inferior_levels.remove(user_id)
        parent.save()
    except ValueError:
        pass
    if parent.parent:
        revoke_user_from_parent_perimeters(perimeter=parent, user_id=user_id)


def revoke_user_from_child_perimeters(perimeter, user_id: int):
    for child in perimeter.children.all():
        try:
            child.allowed_users_above_levels.remove(user_id)
            child.save()
        except ValueError:
            pass
        if child.children.all():
            revoke_user_from_child_perimeters(perimeter=child, user_id=user_id)
