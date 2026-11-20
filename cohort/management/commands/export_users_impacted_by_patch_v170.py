import csv
import io
import json
import re
from collections import defaultdict
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
    "Date de dernière modification de requête",
    "Date de dernière modification de filtre",
    "actif sur les 12 derniers mois",
]


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


def collect_requests() -> tuple[defaultdict[str, set[UUID]], dict[str, datetime]]:
    reqs: defaultdict[str, set[UUID]] = defaultdict(set)
    last_req: dict[str, datetime] = {}
    snapshots = RequestQuerySnapshot.objects.filter(deleted__isnull=True).only("request_id", "owner_id", "created_at", "serialized_query")
    for s in snapshots.iterator():
        if is_impacted_query(s.serialized_query):
            reqs[s.owner_id].add(s.request_id)
            keep_latest(last_req, s.owner_id, s.created_at)
    return reqs, last_req


def collect_filters() -> tuple[defaultdict[str, int], dict[str, datetime]]:
    filts: defaultdict[str, int] = defaultdict(int)
    last_filt: dict[str, datetime] = {}
    filters = FhirFilter.objects.filter(fhir_resource=BIOLOGY, query_version=PREV_VERSION).only("owner_id", "filter", "modified_at")
    for f in filters:
        if filtre_impacte(f.filter):
            filts[f.owner_id] += 1
            keep_latest(last_filt, f.owner_id, f.modified_at)
    return filts, last_filt


def write_csv(
    reqs: defaultdict[str, set[UUID]], last_req: dict[str, datetime], filts: defaultdict[str, int], last_filt: dict[str, datetime]
) -> tuple[str, dict]:
    owners = set(last_req) | set(last_filt)
    since = timezone.now() - timedelta(days=365)
    users = User.objects.filter(username__in=owners).only("username", "email", "firstname", "lastname").order_by("username")
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(HEADER)
    for u in users:
        dr, df = last_req.get(u.username), last_filt.get(u.username)
        last = max(d for d in (dr, df) if d)
        writer.writerow(
            [
                u.username,
                u.email or "",
                u.firstname or "",
                u.lastname or "",
                len(reqs[u.username]),
                filts[u.username],
                dr.date().isoformat() if dr else "",
                df.date().isoformat() if df else "",
                "oui" if last >= since else "non",
            ]
        )

    exported = users.count()
    known = User.objects.all(even_deleted=True).filter(username__in=owners).count()
    stats = {
        "Propriétaires impactés": len(owners),
        "Utilisateurs exportés": exported,
        "Comptes supprimés (non exportés)": known - exported,
        "Absents de la table utilisateurs": len(owners) - known,
        "Requêtes impactées": sum(len(r) for r in reqs.values()),
        "Filtres impactés": sum(filts.values()),
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
        reqs, last_req = collect_requests()
        filts, last_filt = collect_filters()
        return write_csv(reqs, last_req, filts, last_filt)
