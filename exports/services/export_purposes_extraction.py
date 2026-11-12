from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Dict, Iterator, List, Optional
from zoneinfo import ZoneInfo

from django.db.models import Q, QuerySet
from django.utils import timezone

from accesses.models import Access
from accesses.services.accesses import accesses_service
from admin_cohort.types import JobStatus
from exports.enums import ExportPurpose
from exports.models import Export

COLUMNS = [
    "APH",
    "Nom",
    "Prénom",
    "Profil",
    "Périmètre",
    "Adresse mail",
    "Date et heure de l'export",
    "Type d'export",
    "Statut",
    "Motivation",
    "Titre du projet",
    "Porteur du projet",
    "Protocole joint",
    "Date de début du projet",
    "Date de fin du projet",
    "Condition d'exécution",
]

# Same labels as the transfer requests list of the Admin Portal
STATUS_LABELS = {
    JobStatus.finished: "Terminé",
    JobStatus.validated: "Confirmé",
    **dict.fromkeys((JobStatus.new, JobStatus.pending, JobStatus.started), "En cours"),
    JobStatus.denied: "Refusé",
    JobStatus.cancelled: "Annulé",
    JobStatus.failed: "Erreur",
}
UNKNOWN_STATUS_LABEL = "Inconnu"

# Same labels as the purpose choice when creating an export
PURPOSE_LABELS = {
    ExportPurpose.CARE_SUPPORT.value: "Appui au soin",
    ExportPurpose.ACTIVITY_MANAGEMENT.value: "Pilotage de l'activité",
    ExportPurpose.INTERNAL_RESEARCH.value: "Recherche interne",
    ExportPurpose.MULTICENTER_RESEARCH.value: "Recherche multicentrique",
}

# Datetimes are stored in UTC, but the file is read by users in France: dates and date bounds use the Paris time
USERS_TIMEZONE = ZoneInfo("Europe/Paris")
VALUES_SEPARATOR = " | "
DATE_FORMAT = "%d/%m/%Y"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"


class ExportPurposesExtractionService:
    @staticmethod
    def start_of_day(day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=USERS_TIMEZONE)

    def get_exports(self, output_format: List[str], start_date: Optional[date] = None, end_date: Optional[date] = None) -> QuerySet:
        exports = Export.objects.filter(output_format__in=output_format).select_related("owner", "project_details").order_by("created_at")
        if start_date:
            exports = exports.filter(created_at__gte=self.start_of_day(start_date))
        if end_date:
            # Inclusive bound: up to the start of the next day
            exports = exports.filter(created_at__lt=self.start_of_day(end_date + timedelta(days=1)))
        return exports

    @staticmethod
    def get_filename() -> str:
        return f"export_purposes_{timezone.now().astimezone(USERS_TIMEZONE):%Y%m%d}.csv"

    @staticmethod
    def get_profiles_and_perimeters_by_user(user_ids) -> Dict[str, List[tuple]]:
        """For each user, the distinct (role, perimeter) names of their valid accesses"""
        accesses = (
            Access.objects.filter(accesses_service.q_access_is_valid() & Q(profile__is_active=True) & Q(profile__user_id__in=user_ids))
            .select_related("profile", "role", "perimeter")
            .order_by("id")
        )
        names_by_user = defaultdict(dict)
        for access in accesses:
            role_name = (access.role.name or "") if access.role else ""
            perimeter_name = (access.perimeter.name or "") if access.perimeter else ""
            # A dict keeps the order and drops the duplicates, e.g. the same access given through several profiles
            names_by_user[access.profile.user_id][(role_name, perimeter_name)] = None
        return {user_id: list(names) for user_id, names in names_by_user.items()}

    @staticmethod
    def format_date(value: Optional[date]) -> str:
        return value.strftime(DATE_FORMAT) if value else ""

    def build_row(self, export: Export, profiles_and_perimeters: List[tuple]) -> List[str]:
        owner = export.owner
        details = getattr(export, "project_details", None)
        if export.purpose != ExportPurpose.INTERNAL_RESEARCH.value:
            details = None
        return [
            owner.username,
            owner.lastname or "",
            owner.firstname or "",
            # Profiles and perimeters in the same order, so that they can be matched
            VALUES_SEPARATOR.join(role_name for role_name, _ in profiles_and_perimeters),
            VALUES_SEPARATOR.join(perimeter_name for _, perimeter_name in profiles_and_perimeters),
            owner.email or "",
            export.created_at.astimezone(USERS_TIMEZONE).strftime(DATETIME_FORMAT),
            export.output_format.upper(),
            STATUS_LABELS.get(export.request_job_status, UNKNOWN_STATUS_LABEL),
            # Exports made before the purpose was collected have none
            PURPOSE_LABELS.get(export.purpose, ""),
            details.title if details else "",
            details.project_leader if details else "",
            # Protocol: not collected yet
            "",
            self.format_date(details.start_date) if details else "",
            self.format_date(details.end_date) if details else "",
            # Execution condition: not collected yet
            "",
        ]

    def build_rows(self, exports: QuerySet) -> Iterator[List[str]]:
        profiles_and_perimeters_by_user = self.get_profiles_and_perimeters_by_user({export.owner_id for export in exports})
        for export in exports:
            yield self.build_row(export, profiles_and_perimeters_by_user.get(export.owner_id, []))


export_purposes_extraction_service = ExportPurposesExtractionService()
