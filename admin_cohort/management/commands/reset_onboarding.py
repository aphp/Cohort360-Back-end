import logging

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from admin_cohort.models import User
from admin_cohort.tools.cache import invalidate_cache

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Réinitialise le parcours d'onboarding pour tous/quelques utilisateurs"

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument("--all", action="store_true", help="Tous les utilisateurs")
        target.add_argument("--usernames", nargs="+", help="Utilisateurs ciblés")
        parser.add_argument("--dry-run", action="store_true", help="Compte les utilisateurs concernés sans rien modifier")

    def handle(self, *args, **options):
        users = User.objects.filter(Q(onboarding_step__gt=0) | Q(onboarding_completed_at__isnull=False) | Q(charter_signed_at__isnull=False))
        if usernames := options["usernames"]:
            unknown = set(usernames) - set(User.objects.filter(username__in=usernames).values_list("username", flat=True))
            if unknown:
                raise CommandError(f"Utilisateurs introuvables : {', '.join(sorted(unknown))}")
            users = users.filter(username__in=usernames)

        if options["dry_run"]:
            self.stdout.write(f"{users.count()} utilisateur(s) à réinitialiser.")
            return

        count = users.update(onboarding_step=0, onboarding_completed_at=None, charter_signed_at=None, update_datetime=timezone.now())
        invalidate_cache(model_name=User.__name__)

        logger.info("Onboarding réinitialisé pour %s utilisateur(s)", count)
