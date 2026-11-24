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

        manual_accesses = Access.objects.filter(profile__source=MANUAL)
        users = (
            User.objects.filter(
                Q(created_by=admin)
                | Q(updated_by=admin)
                | Q(username__in=manual_accesses.filter(Q(created_by=admin) | Q(updated_by=admin)).values("profile__user")),
                username__in=Profile.objects.filter(source=MANUAL).values("user"),
            )
            .select_related("created_by", "updated_by")
            .order_by("lastname", "firstname", "username")
        )

        now = timezone.now()
        accesses_by_user: dict[str, list[Access]] = {}
        current_accesses = (
            manual_accesses.filter(profile__user__in=users)
            .filter(Q(end_datetime__isnull=True) | Q(end_datetime__gt=now), profile__is_active=True)
            .select_related("profile", "perimeter", "role")
            .order_by("perimeter__name", "role__name", "start_datetime")
        )
        for access in current_accesses:
            accesses_by_user.setdefault(access.profile.user_id, []).append(access)

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";")
        writer.writerow(HEADERS)
        rows = 0
        for user in users:
            user_cols = [user.username, user.lastname, user.firstname, user.email, fmt_user(user.created_by), fmt_user(user.updated_by)]
            # one empty row keeps accounts whose accesses are all closed visible
            for access in accesses_by_user.get(user.username) or [None]:
                access_cols = (
                    [
                        access.perimeter.name if access.perimeter else "",
                        access.role.name if access.role else "",
                        fmt_date(access.start_datetime),
                        fmt_date(access.end_datetime),
                        "Oui" if admin.pk in (access.created_by_id, access.updated_by_id) else "Non",
                    ]
                    if access
                    else [""] * 5
                )
                writer.writerow(user_cols + access_cols)
                rows += 1

        if options["output"]:
            # utf-8-sig so Excel reads accents correctly
            with open(options["output"], "w", encoding="utf-8-sig", newline="") as f:
                f.write(buffer.getvalue())
        else:
            self.stdout.write(buffer.getvalue(), ending="")
        self.stderr.write(f"{users.count()} compte(s), {rows} ligne(s) exportée(s).")
