import csv
import io
import json
import re
from collections import defaultdict
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import unquote

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from admin_cohort.models import User
from cohort.models import FhirFilter, RequestQuerySnapshot

VERSION = "v1.6.4"
ENC = re.compile(r"\bencounter\.[A-Za-z0-9_\-]+")
HEADER = ["Username", "Email", "Prénom", "nom", "Nombre des requêtes impacté", "Nombre des Filtre impacté",
          "Date de dernière modification de requête", "Date de dernière modification de filtre",
          "actif sur les 12 derniers mois"]


def walk(node):
    if isinstance(node, dict) and "criteria" in node:
        for child in node["criteria"]:
            yield from walk(child)
    elif isinstance(node, dict):
        yield node


def filtre_impacte(fhir_filter: str) -> bool:
    for item in (fhir_filter or "").split("&"):
        name, _, value = item.partition("=")
        name = unquote(name)
        if name.startswith("encounter."):
            return True
        if name == "_filter" and ENC.search(unquote(value)):
            return True
    return False


def impacte(criterion: dict) -> bool:
    if criterion.get("resourceType") != "Observation":
        return False
    return filtre_impacte(criterion.get("filterFhir")) or criterion.get("patientAge") is not None


class Command(BaseCommand):
    help = ("Exporte en CSV les utilisateurs dont des requêtes ou des filtres sauvegardés vont être modifiés "
            "par le patch v1.7.0 (migration BC3.3), et l'envoie par email")

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, nargs="+", help="Adresse(s) des destinataires du CSV, séparées par des espaces")
        parser.add_argument("--dry-run", action="store_true", help="Affiche les compteurs sans envoyer d'email")

    def handle(self, *args, **options):
        emails = options["email"]
        invalid = [e for e in emails if not re.match(settings.EMAIL_REGEX, e)]
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
        message = EmailMessage(subject="[Cohort360] Utilisateurs dont des requêtes ou filtres Biologie sont modifiés par la migration BC3.3",
                               body="Ci-joint la liste des utilisateurs dont des requêtes ou des filtres Biologie sauvegardés "
                                    "sont modifiés par la migration BC3.3 (patch v1.7.0).",
                               from_email=settings.DEFAULT_FROM_EMAIL,
                               to=emails)
        message.attach(filename, content.encode("utf-8-sig"), "text/csv")
        try:
            message.send(fail_silently=False)
        except (SMTPException, OSError) as e:
            raise CommandError(f"Échec de l'envoi de l'email : {e}") from e
        self.stdout.write(self.style.SUCCESS(f"CSV envoyé à {', '.join(emails)}"))

    @staticmethod
    def build_csv() -> tuple[str, dict]:
        reqs, filts = defaultdict(set), defaultdict(int)
        last, last_req, last_filt = {}, {}, {}

        snapshots = RequestQuerySnapshot.objects.filter(deleted__isnull=True)\
                                                .only("request_id", "owner_id", "created_at", "serialized_query")
        for s in snapshots.iterator():
            try:
                query = json.loads(s.serialized_query or "{}")
            except ValueError:
                continue
            if query.get("version") != VERSION or query.get("_type") != "request":
                continue
            if not any(impacte(c) for c in walk(query.get("request") or {})):
                continue
            reqs[s.owner_id].add(s.request_id)
            last[s.owner_id] = max(last.get(s.owner_id, s.created_at), s.created_at)
            last_req[s.owner_id] = max(last_req.get(s.owner_id, s.created_at), s.created_at)

        filters = FhirFilter.objects.filter(fhir_resource="Observation", query_version=VERSION)\
                                    .only("owner_id", "filter", "modified_at")
        for f in filters:
            if not filtre_impacte(f.filter):
                continue
            filts[f.owner_id] += 1
            last[f.owner_id] = max(last.get(f.owner_id, f.modified_at), f.modified_at)
            last_filt[f.owner_id] = max(last_filt.get(f.owner_id, f.modified_at), f.modified_at)

        since = timezone.now() - timedelta(days=365)
        users = User.objects.filter(username__in=last.keys())\
                            .only("username", "email", "firstname", "lastname")\
                            .order_by("username")
        out = io.StringIO()
        writer = csv.writer(out, delimiter=";")
        writer.writerow(HEADER)
        for u in users:
            dr, df = last_req.get(u.username), last_filt.get(u.username)
            writer.writerow([u.username, u.email or "", u.firstname or "", u.lastname or "",
                             len(reqs[u.username]), filts[u.username],
                             dr.date().isoformat() if dr else "", df.date().isoformat() if df else "",
                             "oui" if last[u.username] >= since else "non"])

        exported = users.count()
        known = User.objects.all(even_deleted=True).filter(username__in=last.keys()).count()
        stats = {"Propriétaires impactés": len(last),
                 "Utilisateurs exportés": exported,
                 "Comptes supprimés (non exportés)": known - exported,
                 "Absents de la table utilisateurs": len(last) - known,
                 "Requêtes impactées": sum(len(r) for r in reqs.values()),
                 "Filtres impactés": sum(filts.values())}
        return out.getvalue(), stats
