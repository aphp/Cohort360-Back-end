import csv
import io
import re
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from accesses.models import Access, Profile
from accesses.models.access import MANUAL
from admin_cohort.models import User
from admin_cohort.tools.csv_response import CSV_DELIMITER, neutralize_formula

HEADERS = [
    "Identifiant APH",
    "Nom",
    "Prénom",
    "Email",
    "Attribué par",
    "Modifié par",
    "Périmètre",
    "Habilitation",
    "Date de début",
    "Date de fin",
]


def fmt_user(user: User | None) -> str:
    return str(user) if user else ""


def fmt_date(value) -> str:
    return timezone.localtime(value).strftime("%d/%m/%Y") if value else ""


def user_cols(user: User) -> list[str | None]:
    return [user.username, user.lastname, user.firstname, user.email]


def access_cols(access: Access | None) -> list[str | None]:
    if access is None:
        return [""] * 6
    # same fields as « Attribué par / Modifié par » in the Portail Admin accesses table
    return [
        fmt_user(access.created_by),
        fmt_user(access.updated_by),
        access.perimeter.name if access.perimeter else "",
        access.role.name if access.role else "",
        fmt_date(access.start_datetime),
        fmt_date(access.end_datetime),
    ]


def get_users(admin: User):
    by_admin = Q(created_by=admin) | Q(updated_by=admin)
    manual_users = Profile.objects.filter(source=MANUAL).values("user")
    users_via_access = Access.objects.filter(by_admin, profile__source=MANUAL).values("profile__user")
    return User.objects.filter(by_admin | Q(username__in=users_via_access), username__in=manual_users).order_by("lastname", "firstname", "username")


def get_current_accesses_by_user(users) -> dict[str, list[Access]]:
    accesses = (
        Access.objects.filter(profile__source=MANUAL, profile__is_active=True, profile__user__in=users)
        .filter(Q(end_datetime__isnull=True) | Q(end_datetime__gt=timezone.now()))
        .select_related("profile", "perimeter", "role", "created_by", "updated_by")
        .order_by("perimeter__name", "role__name", "start_datetime")
    )
    accesses_by_user: dict[str, list[Access]] = {}
    for access in accesses:
        accesses_by_user.setdefault(access.profile.user_id, []).append(access)
    return accesses_by_user


def build_csv(users) -> tuple[str, int]:
    accesses_by_user = get_current_accesses_by_user(users)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=CSV_DELIMITER)
    writer.writerow(HEADERS)
    rows = 0
    for user in users:
        # one empty row keeps accounts whose accesses are all closed visible
        user_accesses: list[Access | None] = [*accesses_by_user.get(user.username, [])] or [None]
        for access in user_accesses:
            writer.writerow([neutralize_formula(value or "") for value in user_cols(user) + access_cols(access)])
            rows += 1
    return buffer.getvalue(), rows


class Command(BaseCommand):
    help = (
        "Exporte en CSV les comptes créés ou modifiés par un administrateur (compte ou habilitation Manual), "
        "avec leurs habilitations Manual en cours ou à venir, et l'envoie par email"
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Identifiant APH de l'administrateur")
        parser.add_argument(
            "--emails", nargs="+", default=[], help="Adresse(s) des destinataires du CSV, séparées par des espaces (obligatoire sauf en --dry-run)"
        )
        parser.add_argument("--dry-run", action="store_true", help="Affiche les compteurs sans envoyer d'email")

    def handle(self, *args, **options):
        emails = options["emails"]
        if not emails and not options["dry_run"]:
            raise CommandError("--emails est obligatoire (sauf en --dry-run)")
        invalid = [e for e in emails if not re.match(settings.EMAIL_REGEX, e) or not e.lower().endswith("@aphp.fr")]
        if invalid:
            raise CommandError(f"Adresse(s) email invalide(s) : {', '.join(invalid)}")
        admin = User.objects.filter(username=options["username"]).first()
        if admin is None:
            raise CommandError(f"Utilisateur introuvable : {options['username']}")

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            users = get_users(admin)
            content, rows = build_csv(users)
            accounts = users.count()
        self.stdout.write(f"{accounts} compte(s), {rows} ligne(s) exportée(s).")

        if options["dry_run"]:
            self.stdout.write("Dry run : aucun email envoyé.")
            return

        message = EmailMessage(
            subject=f"[Cohort360] Habilitations Manual des comptes créés ou modifiés par {admin.username}",
            body=f"Ci-joint les habilitations Manual en cours des comptes créés ou modifiés par {admin} ({accounts} compte(s)).",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails,
        )
        message.attach(f"3757_habilitations_{admin.username}_{timezone.now():%Y%m%d_%H%M}.csv", content.encode("utf-8-sig"), "text/csv")
        try:
            message.send(fail_silently=False)
        except (SMTPException, OSError) as e:
            raise CommandError(f"Échec de l'envoi de l'email : {e}") from e
        self.stdout.write(self.style.SUCCESS(f"CSV envoyé à {', '.join(emails)}"))
