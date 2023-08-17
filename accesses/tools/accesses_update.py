from accesses.models import Perimeter, Access


def create_children_perimeters_accesses(parents_perimeters: [Perimeter]):
    new_accesses = []
    profiles_updated = []
    perimeter_parent_ids = [perimeter.id for perimeter in parents_perimeters]

    # Récupération des Access d'utilisateurs avec un perimeter GH
    all_access = Access.objects.filter(perimeter_id__in=perimeter_parent_ids)
    # Duplication de l'accès avec le périmètre fils
    for access in all_access:
        # fetch below list perimeters in hierarchy
        perimeter_id = access.perimeter_id
        children_perimeter = Perimeter.objects.filter(parent_id=perimeter_id)

        # copy current access main information
        role = access.role
        profil = access.profile
        start_datetime, end_datetime = access.start_datetime, access.end_datetime

        # duplicate current access with all children perimeters
        for perimeter in children_perimeter:
            user_access = Access(profile=profil, perimeter=perimeter, role=role, start_datetime=start_datetime, end_datetime=end_datetime)
            user_access.save()
            # add accesses for trace
            new_accesses.append(user_access)
        # add profil for trace
        profiles_updated.append(profil.user)
    # Results:
    print(f"New accesses created: {len(new_accesses)}")
    print(f"{len(profiles_updated)} profile.s updated: {profiles_updated}")
