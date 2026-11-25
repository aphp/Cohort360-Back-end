import csv
import io
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from smtplib import SMTPException
from uuid import UUID

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from admin_cohort.models import User
from cohort.models import FhirFilter, RequestQuerySnapshot
from cohort.scripts.patch_requests_v170 import BIOLOGY, PREV_VERSION, is_encounter_filter

HEADER = [
    "Username",
    "Email",
    "Prénom",
    "Nom",
    "Nombre de requêtes impactées",
    "Nombre de filtres impactés",
    "Type",
    "Nom de l'objet",
    "Projet",
    "Identifiant",
    "Date de dernière modification",
    "actif sur les 12 derniers mois",
]
REQUEST, FILTER = "Requête", "Filtre"


@dataclass
class ImpactedObject:
    owner: str
    kind: str
    uuid: UUID
    name: str
    project: str
    modified_at: datetime


def walk(node):
    if isinstance(node, dict) and "criteria" in node:
        for child in node["criteria"]:
            yield from walk(child)
    elif isinstance(node, dict):
        yield node


def filtre_impacte(fhir_filter: str | None) -> bool:
    params = (item.partition("=") for item in (fhir_filter or "").split("&"))
    return any(is_encounter_filter(name, value) for name, _, value in params)


def impacte(criterion: dict) -> bool:
    if criterion.get("resourceType") != BIOLOGY:
        return False
    return filtre_impacte(criterion.get("filterFhir")) or criterion.get("patientAge") is not None


def is_impacted_query(serialized_query: str | None) -> bool:
    try:
        query = json.loads(serialized_query or "{}")
    except ValueError:
        return False
    if query.get("version") != PREV_VERSION or query.get("_type") != "request":
        return False
    return any(impacte(c) for c in walk(query.get("request") or {}))


def keep_latest(dates: dict[str, datetime], owner: str, date: datetime) -> None:
    dates[owner] = max(dates.get(owner, date), date)


def collect_requests() -> list[ImpactedObject]:
    latest: dict[UUID, ImpactedObject] = {}
    snapshots = (
        RequestQuerySnapshot.objects.filter(deleted__isnull=True)
        .select_related("request__parent_folder")
        .only("request_id", "owner_id", "created_at", "serialized_query", "request__name", "request__parent_folder__name")
    )
    for s in snapshots.iterator():
        if not is_impacted_query(s.serialized_query):
            continue
        current = latest.get(s.request_id)
        if current is None or s.created_at > current.modified_at:
            latest[s.request_id] = ImpactedObject(s.owner_id, REQUEST, s.request_id, s.request.name, s.request.parent_folder.name, s.created_at)
    return list(latest.values())


def collect_filters() -> list[ImpactedObject]:
    filters = FhirFilter.objects.filter(fhir_resource=BIOLOGY, query_version=PREV_VERSION).only("uuid", "owner_id", "name", "filter", "modified_at")
    return [ImpactedObject(f.owner_id, FILTER, f.uuid, f.name, "", f.modified_at) for f in filters if filtre_impacte(f.filter)]


def write_csv(objects: list[ImpactedObject]) -> tuple[str, dict]:
    owners = {o.owner for o in objects}
    since = timezone.now() - timedelta(days=365)
    users = {u.username: u for u in User.objects.filter(username__in=owners).only("username", "email", "firstname", "lastname")}
    last_activity: dict[str, datetime] = {}
    counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for o in objects:
        keep_latest(last_activity, o.owner, o.modified_at)
        counts[o.owner][o.kind] += 1
    rows = sorted((o for o in objects if o.owner in users), key=lambda o: (o.owner, o.kind, o.name.lower()))

    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(HEADER)
    previous_owner = None
    for o in rows:
        u = users[o.owner]
        first = o.owner != previous_owner
        previous_owner = o.owner
        writer.writerow(
            [
                u.username,
                u.email or "",
                u.firstname or "",
                u.lastname or "",
                counts[o.owner][REQUEST] if first else "",
                counts[o.owner][FILTER] if first else "",
                o.kind,
                o.name,
                o.project,
                str(o.uuid),
                o.modified_at.date().isoformat(),
                "oui" if last_activity[o.owner] >= since else "non",
            ]
        )

    exported = len(users)
    known = User.objects.all(even_deleted=True).filter(username__in=owners).count()
    stats = {
        "Propriétaires impactés": len(owners),
        "Utilisateurs exportés": exported,
        "Comptes supprimés (non exportés)": known - exported,
        "Absents de la table utilisateurs": len(owners) - known,
        "Requêtes impactées": sum(o.kind == REQUEST for o in objects),
        "Filtres impactés": sum(o.kind == FILTER for o in objects),
        "Lignes exportées": len(rows),
    }
    return out.getvalue(), stats


class Command(BaseCommand):
    help = (
        "Exporte en CSV les utilisateurs dont des requêtes ou des filtres sauvegardés vont être modifiés "
        "par le patch v1.7.0 (migration BC3.3), et l'envoie par email"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email", nargs="+", default=[], help="Adresse(s) des destinataires du CSV, séparées par des espaces (obligatoire sauf en --dry-run)"
        )
        parser.add_argument("--dry-run", action="store_true", help="Affiche les compteurs sans envoyer d'email")

    def handle(self, *args, **options):
        emails = options["email"]
        if not emails and not options["dry_run"]:
            raise CommandError("--email est obligatoire (sauf en --dry-run)")
        invalid = [e for e in emails if not re.match(settings.EMAIL_REGEX, e) or not e.lower().endswith("@aphp.fr")]
        if invalid:
            raise CommandError(f"Adresse(s) email invalide(s) : {', '.join(invalid)}")

        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
            content, stats = self.build_csv()

        for label, value in stats.items():
            self.stdout.write(f"{label:<35}: {value}")

        if options["dry_run"]:
            self.stdout.write("Dry run : aucun email envoyé.")
            return

        filename = f"3580_utilisateurs_{timezone.now():%Y%m%d_%H%M}.csv"
        message = EmailMessage(
            subject="[Cohort360] Utilisateurs dont des requêtes ou filtres Biologie sont modifiés par la migration BC3.3",
            body="Ci-joint la liste des utilisateurs dont des requêtes ou des filtres Biologie sauvegardés "
            "sont modifiés par la migration BC3.3 (patch v1.7.0).",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=emails,
        )
        message.attach(filename, content.encode("utf-8-sig"), "text/csv")
        try:
            message.send(fail_silently=False)
        except (SMTPException, OSError) as e:
            raise CommandError(f"Échec de l'envoi de l'email : {e}") from e
        self.stdout.write(self.style.SUCCESS(f"CSV envoyé à {', '.join(emails)}"))

    @staticmethod
    def build_csv() -> tuple[str, dict]:
        return write_csv(collect_requests() + collect_filters())
