import csv
import io

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from accesses.models import Access, Profile
from accesses.models.access import MANUAL
from admin_cohort.models import User

HEADERS = [
    "Identifiant APH",
    "Nom",
    "Prénom",
    "Email",
    "Créé par",
    "Modifié par",
    "Périmètre",
    "Habilitation",
    "Date de début",
    "Date de fin",
    "Créée ou modifiée par l'admin",
]


def fmt_user(user: User | None) -> str:
    return str(user) if user else ""


def fmt_date(value) -> str:
    return timezone.localtime(value).strftime("%d/%m/%Y") if value else ""


def user_cols(user: User) -> list[str | None]:
    return [user.username, user.lastname, user.firstname, user.email, fmt_user(user.created_by), fmt_user(user.updated_by)]


def access_cols(access: Access | None, admin: User) -> list[str | None]:
    if access is None:
        return [""] * 5
    return [
        access.perimeter.name if access.perimeter else "",
        access.role.name if access.role else "",
        fmt_date(access.start_datetime),
        fmt_date(access.end_datetime),
        "Oui" if admin.pk in (access.created_by_id, access.updated_by_id) else "Non",
    ]


def get_users(admin: User):
    by_admin = Q(created_by=admin) | Q(updated_by=admin)
    manual_users = Profile.objects.filter(source=MANUAL).values("user")
    users_via_access = Access.objects.filter(by_admin, profile__source=MANUAL).values("profile__user")
    return (
        User.objects.filter(by_admin | Q(username__in=users_via_access), username__in=manual_users)
        .select_related("created_by", "updated_by")
        .order_by("lastname", "firstname", "username")
    )


def get_current_accesses_by_user(users) -> dict[str, list[Access]]:
    accesses = (
        Access.objects.filter(profile__source=MANUAL, profile__is_active=True, profile__user__in=users)
        .filter(Q(end_datetime__isnull=True) | Q(end_datetime__gt=timezone.now()))
        .select_related("profile", "perimeter", "role")
        .order_by("perimeter__name", "role__name", "start_datetime")
    )
    accesses_by_user: dict[str, list[Access]] = {}
    for access in accesses:
        accesses_by_user.setdefault(access.profile.user_id, []).append(access)
    return accesses_by_user


class Command(BaseCommand):
    help = (
        "Exporte en CSV les comptes créés ou modifiés par un administrateur (compte ou habilitation Manual), "
        "avec leurs habilitations Manual en cours ou à venir"
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Identifiant APH de l'administrateur")
        parser.add_argument("--output", help="Chemin du fichier CSV (par défaut : sortie standard)")

    def handle(self, *args, **options):
        admin = User.objects.filter(username=options["username"]).first()
        if admin is None:
            raise CommandError(f"Utilisateur introuvable : {options['username']}")

        users = get_users(admin)
        accesses_by_user = get_current_accesses_by_user(users)

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(HEADERS)
        rows = 0
        for user in users:
            # one empty row keeps accounts whose accesses are all closed visible
            for access in accesses_by_user.get(user.username) or [None]:
                writer.writerow(user_cols(user) + access_cols(access, admin))
                rows += 1

        if options["output"]:
            # utf-8-sig so Excel reads accents correctly
            with open(options["output"], "w", encoding="utf-8-sig", newline="") as f:
                f.write(buffer.getvalue())
        else:
            self.stdout.write(buffer.getvalue(), ending="")
        self.stderr.write(f"{users.count()} compte(s), {rows} ligne(s) exportée(s).")
